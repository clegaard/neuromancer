"""
Nonlinear ODEs. Wrapper for emulator dynamical models

    + Internal Emulators - in house ground truth equations
    + External Emulators - third party models

References:

    + https://en.wikipedia.org/wiki/List_of_nonlinear_ordinary_differential_equations
    + https://en.wikipedia.org/wiki/List_of_dynamical_systems_and_differential_equations_topics
"""
# Core python
import inspect, sys, functools
# Numerical, ML
import scipy, torch, torchdiffeq, numpy


def grad(tensor, requires_grad):
    tensor.requires_grad = requires_grad
    return tensor


class Backend:
    numpy_backend = {'odeint': functools.partial(scipy.integrate.odeint, tfirst=True),
                     'cat': numpy.concatenate,
                     'cast': numpy.array,
                     'core': numpy,
                     'grad': lambda x, requires_grad: x,
                     'seed': numpy.random.seed}
    torch_backend = {'odeint': torchdiffeq.odeint,
                     'cat': torch.cat,
                     'cast': torch.tensor,
                     'core': torch,
                     'grad': grad,
                     'seed': torch.manual_seed}
    backends = {'torch': torch_backend,
                'numpy': numpy_backend}

    def __init__(self, backend):
        """
        backend: can be torch or numpy
        """
        for k, v in Backend.backends[backend].items():
            setattr(self, k, v)


"""
Base Classes for dynamic systems emulators

"""
from abc import ABC, abstractmethod
import random
import numpy as np


class ODE_Autonomous(torch.nn.Module):
    """
    base class autonomous ODE
    """
    def __init__(self, nsim=1001, ninit=0., ts=0.1, seed=59, x0=0., backend='numpy', requires_grad=False):
        super().__init__()
        self.B = Backend(backend)

        random.seed(seed)
        self.B.seed(seed)
        self.seed = seed

        self.nsim, self.ninit, self.ts, self.x0 = nsim, ninit, ts, self.B.cast(x0)

    def get_stats(self):
        """
        Get a hyperbox defined by min and max values on each of nx axes. Used to sample initial conditions for simulations.
        Box is generated by simulating system with step size ts for nsim steps and then taking the min and max along each axis

        :param system: (psl.ODE_NonAutonomous)
        :param ts: (float) Timestep interval size
        :param nsim: (int) Number of simulation steps to use in defining box
        """
        sim = self.simulate()
        X = sim['X']
        return {'min': X.min(axis=0), 'max': X.max(axis=0),
                'mean': X.mean(axis=0), 'var': X.var(axis=0),
                'std': X.std(axis=0)}

    def get_x0(self):
        """
        Randomly sample an initial condition

        :param box: Dictionary with keys 'min' and 'max' and values np.arrays with shape=(nx,)
        """
        return np.random.uniform(low=self.xstats['min'], high=self.xstats['max'])

    def set_params(self, parameters, requires_grad):
        return [self.B.grad(self.B.cast(p), requires_grad) for p in parameters]

    def simulate(self, ninit=None, nsim=None, Time=None, ts=None, x0=None):

        """
        :param nsim: (int) Number of steps for open loop response
        :param ninit: (float) initial simulation time
        :param ts: (float) step size, sampling time
        :param x0: (float) state initial conditions
        :return: The response matrices, i.e. X
        """
        ninit = ninit if ninit is not None else self.ninit
        nsim = nsim if nsim is not None else self.nsim
        ts = ts if ts is not None else self.ts
        x0 = x0 if x0 is not None else self.x0
        Time = Time if Time is not None else self.B.core.arange(0, nsim+1) * ts + ninit
        assert x0.shape[0] % self.nx == 0, "Mismatch in x0 size"

        X = self.B.odeint(self.equations, x0, Time)
        return {'Y': X.reshape(nsim+1, -1), 'X': X}


class UniversalOscillator(ODE_Autonomous):
    """
    Harmonic oscillator

    + https://en.wikipedia.org/wiki/Harmonic_oscillator
    + https://sam-dolan.staff.shef.ac.uk/mas212/notebooks/ODE_Example.html
    """

    def __init__(self, nsim=1001, ninit=0, ts=0.1, seed=59, backend='numpy', requires_grad=False):
        super().__init__(nsim=nsim, ninit=ninit, ts=ts, seed=seed, backend=backend, requires_grad=requires_grad)
        mu = 2.
        omega = 1.
        self.parameters = [mu, omega]
        self.mu, self.omega = self.set_params([mu, omega], requires_grad)

        self.x0 = self.B.cast([1.0, 0.0])
        self.nx = 2
        self.xstats = self.get_stats()

    def equations(self, t, x):
        dx1 = x[1]
        dx2 = -2.*self.mu*x[1] - x[0] + self.B.core.cos(self.omega*t)
        return self.B.cast([dx1, dx2])


class Pendulum(ODE_Autonomous):
    """
    Simple pendulum.

    + https://docs.scipy.org/doc/scipy/reference/generated/scipy.integrate.odeint.html
    """

    def __init__(self, nsim=1001, ninit=0, ts=0.1, seed=59, backend='numpy', requires_grad=False):
        super().__init__(nsim=nsim, ninit=ninit, ts=ts, seed=seed, backend=backend, requires_grad=requires_grad)
        g = 9.81
        f = 3.
        self.g, self.f = self.set_params([g, f], requires_grad)

        self.nx = 2
        self.x0 = self.B.cast([0., 1.])
        self.xstats = self.get_stats()

    def equations(self, t, x):
        theta = x[0]
        omega = x[1]
        return self.B.cast([omega, -self.f*omega - self.g*self.B.core.sin(theta)])


class DoublePendulum(ODE_Autonomous):
    """
    Double Pendulum
    https://scipython.com/blog/the-double-pendulum/
    """

    def __init__(self, nsim=1001, ninit=0, ts=0.1, seed=59, backend='numpy', requires_grad=False):
        super().__init__(nsim=nsim, ninit=ninit, ts=ts, seed=seed, backend=backend, requires_grad=requires_grad)
        L1 = 1.
        L2 = 1.
        m1 = 1.
        m2 = 1.
        g = 9.81
        self.L1, self.L2, self.m1, self.m2, self.g = self.set_params([L1, L2, m1, m2, g], requires_grad)

        self.x0 = self.B.cast([3 * self.B.core.pi / 7, 0, 3 * self.B.core.pi / 4, 0])
        self.nx = 4.
        self.xstats = self.get_stats()

    def equations(self, t, x):
        theta1 = x[0]
        z1 = x[1]
        theta2 = x[2]
        z2 = x[3]
        c, s = self.B.core.cos(theta1 - theta2), self.B.core.sin(theta1 - theta2)
        dx1 = z1
        dx2 = (self.m2 * self.g * self.B.core.sin(theta2) * c - self.m2 * s * (self.L1 * z1 ** 2 * c + self.L2 * z2 ** 2) -
               (self.m1 + self.m2) * self.g * self.B.core.sin(theta1)) / self.L1 / (self.m1 + self.m2 * s ** 2)
        dx3 = z2
        dx4 = ((self.m1 + self.m2) * (self.L1 * z1 ** 2 * s - self.g * self.B.core.sin(theta2) + self.g * self.B.core.sin(theta1) * c) +
               self.m2 * self.L2 * z2 ** 2 * s * c) / self.L2 / (self.m1 + self.m2 * s ** 2)
        return self.B.cast([dx1, dx2, dx3, dx4])


class Lorenz96(ODE_Autonomous):
    """
    Lorenz 96 model

    + https://en.wikipedia.org/wiki/Lorenz_96_model
    """

    def __init__(self, nsim=1001, ninit=0, ts=0.1, seed=59, backend='numpy', requires_grad=False):
        super().__init__(nsim=nsim, ninit=ninit, ts=ts, seed=seed, backend=backend, requires_grad=requires_grad)
        F = 8.  # Forcing
        self.F, = self.set_params([F], requires_grad)

        self.N = 36  # Number of variables
        self.x0 = self.F*self.B.core.ones(self.N)
        self.x0[19] += 0.01  # Add small perturbation to random variable
        self.nx = self.N
        self.xstats = self.get_stats()

    def equations(self, t, x):
        dx = self.B.core.zeros(self.N)
        # First the 3 edge cases: i=1,2,N
        dx[0] = (x[1] - x[self.N - 2]) * x[self.N - 1] - x[0]
        dx[1] = (x[2] - x[self.N - 1]) * x[0] - x[1]
        dx[self.N - 1] = (x[0] - x[self.N - 3]) * x[self.N - 2] - x[self.N - 1]
        # Then the general case
        for i in range(2, self.N - 1):
            dx[i] = (x[i + 1] - x[i - 2]) * x[i - 1] - x[i]
        # Add the forcing term
        return dx + self.F


class LorenzSystem(ODE_Autonomous):
    """
    Lorenz System

    + https://en.wikipedia.org/wiki/Lorenz_system#Analysis
    + https://ipywidgets.readthedocs.io/en/stable/examples/Lorenz%20Differential%20Equations.html
    + https://scipython.com/blog/the-lorenz-attractor/
    + https://matplotlib.org/3.1.0/gallery/mplot3d/lorenz_attractor.html
    """

    def __init__(self, nsim=1001, ninit=0, ts=0.1, seed=59, backend='numpy', requires_grad=False):
        super().__init__(nsim=nsim, ninit=ninit, ts=ts, seed=seed, backend=backend, requires_grad=requires_grad)
        rho = 28.0
        sigma = 10.0
        beta = 8.0 / 3.0
        self.rho, self.sigma, self.beta = self.set_params([rho, sigma, beta], requires_grad)

        self.x0 = self.B.cast([1.0, 1.0, 1.0])
        self.nx = 3
        self.xstats = self.get_stats()

    def equations(self, t, x):
        dx1 = self.sigma*(x[1] - x[0])
        dx2 = x[0]*(self.rho - x[2]) - x[1]
        dx3 = x[0]*x[1] - self.beta*x[2]
        return self.B.cast([dx1, dx2, dx3])


class VanDerPol(ODE_Autonomous):
    """
    Van der Pol oscillator

    + https://en.wikipedia.org/wiki/Van_der_Pol_oscillator
    + http://kitchingroup.cheme.cmu.edu/blog/2013/02/02/Solving-a-second-order-ode/
    """

    def __init__(self, nsim=1001, ninit=0, ts=0.1, seed=59, backend='numpy', requires_grad=False):
        super().__init__(nsim=nsim, ninit=ninit, ts=ts, seed=seed, backend=backend, requires_grad=requires_grad)
        mu = 1.0
        self.mu, = self.set_params([mu], requires_grad)

        self.x0 = self.B.cast([1., 2.])
        self.nx = 2
        self.xstats = self.get_stats()

    def equations(self, t, x):
        dx1 = self.mu*(x[0] - 1./3.*x[0]**3 - x[1])
        dx2= x[0]/self.mu
        return self.B.cast([dx1, dx2])


class ThomasAttractor(ODE_Autonomous):
    """
    Thomas' cyclically symmetric attractor

    + https://en.wikipedia.org/wiki/Thomas%27_cyclically_symmetric_attractor
    """

    def __init__(self, nsim=1001, ninit=0, ts=0.1, seed=59, backend='numpy', requires_grad=False):
        super().__init__(nsim=nsim, ninit=ninit, ts=ts, seed=seed, backend=backend, requires_grad=requires_grad)
        b = 0.208186
        self.b, = self.set_params([b], requires_grad)

        self.x0 = self.B.cast([1., -1., 1.])
        self.nx = 3
        self.xstats = self.get_stats()

    def equations(self, t, x):
        dx1 = self.B.core.sin(x[1]) - self.b*x[0]
        dx2 = self.B.core.sin(x[2]) - self.b*x[1]
        dx3 = self.B.core.sin(x[0]) - self.b*x[2]
        return self.B.cast([dx1, dx2, dx3])


class RosslerAttractor(ODE_Autonomous):
    """
    Rössler attractor

    + https://en.wikipedia.org/wiki/R%C3%B6ssler_attractor
    """

    def __init__(self, nsim=1001, ninit=0, ts=0.1, seed=59, backend='numpy', requires_grad=False):
        super().__init__(nsim=nsim, ninit=ninit, ts=ts, seed=seed, backend=backend, requires_grad=requires_grad)
        a = 0.2
        b = 0.2
        c = 5.7
        self.a, self.b, self.c = self.set_params([a, b, c], requires_grad)

        self.x0 = self.B.cast([0., 0., 0.])
        self.nx = 3
        self.xstats = self.get_stats()

    def equations(self, t, x):
        dx1 = - x[1] - x[2]
        dx2 = x[0] + self.a*x[1]
        dx3 = self.b + x[2]*(x[0]-self.c)
        return self.B.cast([dx1, dx2, dx3])


class LotkaVolterra(ODE_Autonomous):
    """
    Lotka–Volterra equations, also known as the predator–prey equations

    + https://en.wikipedia.org/wiki/Lotka%E2%80%93Volterra_equations
    """

    def __init__(self, nsim=1001, ninit=0, ts=0.1, seed=59, backend='numpy', requires_grad=False):
        super().__init__(nsim=nsim, ninit=ninit, ts=ts, seed=seed, backend=backend, requires_grad=requires_grad)
        a = 1.
        b = 0.1
        c = 1.5
        d = 0.75
        self.a, self.b, self.c, self.d = self.set_params([a, b, c, d], requires_grad)

        self.x0 = self.B.cast([5., 100.])
        self.nx = 2
        self.xstats = self.get_stats()

    def equations(self, t, x):
        dx1 = self.a*x[0] - self.b*x[0]*x[1]
        dx2 = -self.c*x[1] + self.d*self.b*x[0]*x[1]
        return self.B.cast([dx1, dx2])


class Brusselator1D(ODE_Autonomous):
    """
    Brusselator

    + https://en.wikipedia.org/wiki/Brusselator
    """

    def __init__(self, nsim=1001, ninit=0, ts=0.1, seed=59, backend='numpy', requires_grad=False):
        super().__init__(nsim=nsim, ninit=ninit, ts=ts, seed=seed, backend=backend, requires_grad=requires_grad)
        a = 1.0
        b = 3.0
        self.a, self.b = self.set_params([a, b], requires_grad)
        self.x0 = self.B.cast([1.0, 1.0])
        self.nx = 2
        self.xstats = self.get_stats()

    def equations(self, t, x):
        dx1 = self.a + x[1]*x[0]**2 -self.b*x[0] - x[0]
        dx2 = self.b*x[0] - x[1]*x[0]**2
        return self.B.cast([dx1, dx2])


class ChuaCircuit(ODE_Autonomous):
    """
    Chua's circuit

    + https://en.wikipedia.org/wiki/Chua%27s_circuit
    + https://www.chuacircuits.com/matlabsim.php
    """

    def __init__(self, nsim=1001, ninit=0, ts=0.1, seed=59, backend='numpy', requires_grad=False):
        super().__init__(nsim=nsim, ninit=ninit, ts=ts, seed=seed, backend=backend, requires_grad=requires_grad)
        # parameters
        a = 15.6
        b = 28.0
        m0 = -1.143
        m1 = -0.714
        self.a, self.b, self.m0, self.m1 = self.set_params([a, b, m0, m1], requires_grad)

        self.x0 = self.B.cast([0.7, 0.0, 0.0])
        self.nx = 3
        self.xstats = self.get_stats()

    def equations(self, t, x):
        fx = self.m1*x[0] + 0.5*(self.m0 - self.m1)*(self.B.core.abs(x[0] + 1) - self.B.core.abs(x[0] - 1))
        dx1 = self.a*(x[1] - x[0] - fx)
        dx2 = x[0] - x[1] + x[2]
        dx3 = -self.b*x[1]
        return self.B.cast([dx1, dx2, dx3])


class Duffing(ODE_Autonomous):
    """
    Duffing equation

    + https://en.wikipedia.org/wiki/Duffing_equation
    """

    def __init__(self, nsim=3001, ninit=0, ts=0.01, seed=59, backend='numpy', requires_grad=False):
        super().__init__(nsim=nsim, ninit=ninit, ts=ts, seed=seed, backend=backend, requires_grad=requires_grad)
        delta = 0.02
        alpha = 1.
        beta = 5.
        gamma = 8.
        omega = 0.5
        self.delta, self.alpha, self.beta, self.gamma, self.omega = self.set_params([delta, alpha, beta, gamma, omega], requires_grad)

        self.x0 = self.B.cast([1.0, 0.0])
        self.nx = 2
        self.xstats = self.get_stats()

    def equations(self, t, x):
        dx1 = x[1]
        dx2 = - self.delta*x[1] - self.alpha*x[0] - self.beta*x[0]**3 + self.gamma*self.B.core.cos(self.omega*t)
        return self.B.cast([dx1, dx2])


class Autoignition(ODE_Autonomous):
    """
    ODE describing pulsating instability in open-ended combustor.

    + Koch, J., Kurosaka, M., Knowlen, C., Kutz, J.N.,
      "Multiscale physics of rotating detonation waves: Autosolitons and modulational instabilities,"
      Physical Review E, 2021
    """

    def __init__(self, nsim=1001, ninit=0, ts=0.1, seed=59, backend='numpy', requires_grad=False):
        super().__init__(nsim=nsim, ninit=ninit, ts=ts, seed=seed, backend=backend, requires_grad=requires_grad)
        alpha = 0.3
        uc = 1.1
        s = 1.0
        k = 1.0
        r = 5.0
        q = 6.5
        up = 0.55
        e = 1.0
        self.alpha, self.uc, self.s, self.k, self.r, self.q, self.up, self.e = self.set_params([alpha, uc, s, k, r, q, up, e], requires_grad)

        self.x0 = self.B.cast([1.0, 0.7])
        self.nx = 2
        self.xstats = self.get_stats()

    def equations(self, t, x):
        reactionRate = self.k * (1.0 - x[1]) * self.B.core.exp((x[0] - self.uc) / self.alpha)
        regenRate = self.s * self.up * x[1] / (1.0 + self.B.core.exp(self.r * (x[0] - self.up)))
        dx1 = self.q * reactionRate - self.e * x[0] ** 2
        dx2 = reactionRate - regenRate
        return self.B.cast([dx1, dx2])


systems = dict(inspect.getmembers(sys.modules[__name__], lambda x: inspect.isclass(x)))
systems = {k: v for k, v in systems.items() if issubclass(v, ODE_Autonomous) and v is not ODE_Autonomous}

