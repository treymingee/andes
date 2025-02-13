"""
Integration methods for DAE.
"""

import logging
import numpy as np

from andes.shared import sparse, matrix, tqdm


logger = logging.getLogger(__name__)


class ImplicitIter:
    """
    Base class for implicit iterative methods.
    """

    @staticmethod
    def calc_jac(tds, gxs, gys):
        pass

    @staticmethod
    def calc_q(x, f, Tf, h, x0, f0):
        pass

    @staticmethod
    def step(tds):
        """
        Integrate with Implicit Trapezoidal Method (ITM) to the current time.

        This function has an internal Newton-Raphson loop for algebraized semi-explicit DAE.
        The function returns the convergence status when done but does NOT progress simulation time.

        Returns
        -------
        bool
            Convergence status in ``tds.converged``.

        """
        system = tds.system
        dae = tds.system.dae

        if tds.h == 0:
            logger.error("Current step size is zero. Integration is not permitted.")
            return False

        tds.mis = [1, 1]
        tds.niter = 0
        tds.converged = False

        tds.x0[:] = dae.x
        tds.y0[:] = dae.y
        tds.f0[:] = dae.f

        while True:
            tds.fg_update(models=system.exist.pflow_tds)

            # lazy Jacobian update

            reason = ''
            if dae.t == 0:
                reason = 't=0'
            elif tds.config.honest:
                reason = 'using honest method'
            elif tds.custom_event:
                reason = 'custom event set'
            elif not tds.last_converged:
                reason = 'non-convergence in the last step'
            elif tds.niter > 4 and (tds.niter + 1) % 3 == 0:
                reason = 'update every 6 iterations'
            elif dae.t - tds._last_switch_t < 0.1:
                reason = 'within 0.1s of event'

            if reason:
                system.j_update(models=system.exist.pflow_tds, info=reason)

                # set flag in `solver.worker.factorize`, not `solver.factorize`.
                tds.solver.worker.factorize = True

            # `Tf` should remain constant throughout the simulation, even if the corresponding diff. var.
            # is pegged by the anti-windup limiters.

            # solve implicit trapezoidal method (ITM) integration
            if tds.config.g_scale > 0:
                gxs = tds.config.g_scale * tds.h * dae.gx
                gys = tds.config.g_scale * tds.h * dae.gy
            else:
                gxs = dae.gx
                gys = dae.gy

            # calculate complete Jacobian matrix ``Ac```
            tds.Ac = tds.method.calc_jac(tds, gxs, gys)

            # equation `tds.qg[:dae.n] = 0` is the implicit form of differential equations using ITM
            tds.qg[:dae.n] = tds.method.calc_q(dae.x, dae.f, dae.Tf, tds.h, tds.x0, tds.f0)

            # reset the corresponding q elements for pegged anti-windup limiter
            for item in system.antiwindups:
                for key, _, eqval in item.x_set:
                    np.put(tds.qg, key, eqval)

            # set or scale the algebraic residuals
            if tds.config.g_scale > 0:
                tds.qg[dae.n:] = tds.config.g_scale * tds.h * dae.g
            else:
                tds.qg[dae.n:] = dae.g

            # calculate variable corrections
            if not tds.config.linsolve:
                inc = tds.solver.solve(tds.Ac, matrix(tds.qg))
            else:
                inc = tds.solver.linsolve(tds.Ac, matrix(tds.qg))

            # check for np.nan first
            if np.isnan(inc).any():
                tds.err_msg = 'NaN found in solution. Convergence is not likely'
                tds.niter = tds.config.max_iter + 1
                tds.busted = True
                break

            # reset small values to reduce chattering
            inc[np.where(np.abs(inc) < tds.tol_zero)] = 0

            # set new values
            dae.x -= inc[:dae.n].ravel()
            dae.y -= inc[dae.n: dae.n + dae.m].ravel()

            # synchronize solutions to model internal storage
            system.vars_to_models()

            # store `inc` to tds for debugging
            tds.inc = inc

            mis = np.max(np.abs(inc))

            # store initial maximum mismatch
            if tds.niter == 0:
                tds.mis[0] = mis
            else:
                tds.mis[-1] = mis

            tds.niter += 1

            # converged
            if mis <= tds.config.tol:
                tds.converged = True
                break

            # non-convergence cases
            if tds.niter > tds.config.max_iter:
                tqdm.write(f'* Max. iter. {tds.config.max_iter} reached for t={dae.t:.6f}s, '
                           f'h={tds.h:.6f}s, max inc={mis:.4g} ')

                # debug helpers
                g_max = np.argmax(abs(dae.g))
                inc_max = np.argmax(abs(inc))
                tds._debug_g(g_max)
                tds._debug_ac(inc_max)
                break

            if (mis > 1e6) and (mis > 1e6 * tds.mis[0]):
                tds.err_msg = 'Error increased too quickly.'
                break

        if not tds.converged:
            dae.x[:] = np.array(tds.x0)
            dae.y[:] = np.array(tds.y0)
            dae.f[:] = np.array(tds.f0)
            system.vars_to_models()

        tds.last_converged = tds.converged

        return tds.converged


class BackEuler(ImplicitIter):
    """
    Backward Euler's integration method.
    """
    @staticmethod
    def calc_jac(tds, gxs, gys):
        """
        Build full Jacobian matrix ``Ac`` for Trapezoid method.
        """

        dae = tds.system.dae

        return sparse([[tds.Teye - tds.h * dae.fx, gxs],
                       [-tds.h * dae.fy, gys]], 'd')

    @staticmethod
    def calc_q(x, f, Tf, h, x0, f0):
        """
        Calculate the residual of algebraized differential equations.

        Notes
        -----
        Numba jit somehow slows down this function for the 14-bus
        and the 2k-bus systems.
        """

        return Tf * (x - x0) - h * f


class Trapezoid(ImplicitIter):
    """
    Trapezoidal methods.
    """

    @staticmethod
    def calc_jac(tds, gxs, gys):
        """
        Build full Jacobian matrix ``Ac`` for Trapezoid method.
        """

        dae = tds.system.dae

        return sparse([[tds.Teye - tds.h * 0.5 * dae.fx, gxs],
                       [-tds.h * 0.5 * dae.fy, gys]], 'd')

    @staticmethod
    def calc_q(x, f, Tf, h, x0, f0):
        """
        Calculate the residual of algebraized differential equations.

        Notes
        -----
        Numba jit somehow slows down this function for the 14-bus
        and the 2k-bus systems.
        """

        return Tf * (x - x0) - h * 0.5 * (f + f0)


# --- solution method name-to-class mapping ---
# !!! add new solvers to below

method_map = {"trapezoid": Trapezoid,
              "backeuler": BackEuler,
              }
