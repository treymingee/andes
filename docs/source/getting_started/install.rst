.. _install:

************
Installation
************

New to Python
=============

.. _Setup Mambaforge:

Setting Up Mambaforge
---------------------
If you are new to Python and want to get started quickly, you can use
Mambaforge, which is a conda-like package manager configured with conda-forge.

Step 1:

Downloaded the latest Mambaforge for your platform from
https://github.com/conda-forge/miniforge#mambaforge.
Most users will use ``x86_64(amd64)`` for Intel and AMD processors.
Mac users with Apple Silicon should use ``arm64(Apple Silicon)``
for best performance.

Next, complete the Mambaforge installation on your system.

.. note::

    Mambaforge is a drop-in replacement for conda. If you have an existing
    conda installation, you can replace all following ``mamba`` commands
    with ``conda`` and achieve the same functionality.

    If you are using Anaconda or Miniconda on Windows, you should open
    ``Anaconda Prompt`` instead of ``Miniforge Prompt``.

Step 2:

Open Terminal (on Linux or maxOS) or `Miniforge Prompt` (on Windows, **not cmd!!**).
Make sure you are in a conda environment - you should see ``(base)`` prepended to the
command-line prompt, such as ``(base) C:\Users\username>``.

Create an environment for ANDES (recommended)

.. code:: bash

     mamba create --name andes python=3.8

Activate the new environment with

.. code:: bash

     mamba activate andes

.. note::

    You will need to activate the ``andes`` environment every time
    in a new Miniforge Prompt or shell.

If these steps complete without error, you now have a working Python environment.
See the commands at the top to :ref:`getting-started` ANDES.

.. _Develop Install:

Develop Install
===============

The development mode installation is for users who want to modify
the code and, for example, develop new models or routines.
The benefit of development mode installation is that
changes to source code will be reflected immediately without re-installation.

Step 1: Get ANDES source code

As a developer, you are strongly encouraged to clone the source code using ``git``
from either your fork or the original repository. Clone the repository with

.. code:: bash

    git clone https://github.com/cuihantao/andes

You can replace the URL with your own fork.
Using ``git``, you can later easily version control and update the source code.

Alternatively, you can download the ANDES source code from
https://github.com/cuihantao/andes and extract all files to the path of your choice.
Although this will work, this is discouraged, since tracking changes and
pushing back code would be painful.

.. _`Step 2`:

Step 2: Install dependencies

In the Mambaforge environment, use ``cd`` to change directory to the ANDES root folder.
The folder should contain the ``setup.py`` file.

Install dependencies with

.. code:: bash

    mamba install --file requirements.txt
    mamba install --file requirements-dev.txt

Alternatively, you can install them with ``pip``:

.. code:: bash

    pip install -r requirements.txt
    pip install -r requirements-dev.txt

Step 3: Install ANDES in the development mode using

.. code:: bash

      python3 -m pip install -e .

Note the dot at the end. Pip will take care of the rest.

.. note::

    The ANDES version number shown in ``pip list``
    will stuck at the version that was intalled, unless
    ANDES is develop-installed again.
    It will not update automatically with ``git pull``.

    To check the latest version number, check the preamble
    by running the ``andes`` command or chek the output of
    ``python -c "import andes; print(andes.__version__)"``

.. note::

    ANDES updates may infrequently introduce new package
    requirements. If you see an ``ImportError`` after updating
    ANDES, you can manually install the missing dependencies
    or redo `Step 2`_.

Updating ANDES
==============

Regular ANDES updates will be pushed to both ``conda-forge`` and Python package index.
It is recommended to use the latest version for bug fixes and new features.
We also recommended you to check the :ref:`ReleaseNotes` before updating to stay informed
of changes that might break your downstream code.

Depending you how you installed ANDES, you will use one of the following ways to upgrade.

If you installed it from mamba or conda, run

.. code:: bash

    conda install -c conda-forge --yes andes

If you install it from PyPI (namely, through ``pip``), run

.. code:: bash

    python3 -m pip install --yes andes


Troubleshooting
===============

If you get an error message on Windows, reading ::

    ImportError: DLL load failed: The specified module could not be found.

It is a path issue of your Python. In fact, Python on Windows is so broken that
many people are resorting to WSL2 just for Python. Fixes can be convoluted, but
the easiest one is to install ANDES in a Conda/Mambaforge environment.
