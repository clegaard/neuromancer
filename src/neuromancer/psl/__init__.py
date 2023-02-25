import neuromancer.psl.autonomous as auto
import neuromancer.psl.nonautonomous as nauto
import neuromancer.psl.ssm as ssm
import neuromancer.psl.coupled_systems as cs
import neuromancer.psl.emulator as emulator
import neuromancer.psl.plot as plot
from neuromancer.psl.perturb import *
import toml
import os

try:
    with open("pyproject.toml") as f:
        _pyproject = toml.load(f)

    repo = _pyproject["project"]["urls"]["repository"]
    'https://github.com/clegaard/neuromancer/'
except Exception as e:
    raise RuntimeError("Unable to extract the project.urls.repository from `pyproject.toml`") from e

resource_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

datasets = {
    k: os.path.join(resource_path, v) for k, v in {
        "tank": "NLIN_SISO_two_tank/NLIN_two_tank_SISO.mat",
        "vehicle3": "NLIN_MIMO_vehicle/NLIN_MIMO_vehicle3.mat",
        "aero": "NLIN_MIMO_Aerodynamic/NLIN_MIMO_Aerodynamic.mat",
        "flexy_air": "Flexy_air/flexy_air_data.csv",
        "EED_building": "EED_building/EED_building.csv",
        "9bus_test": "9bus_test",
        "9bus_init": "9bus_perturbed_init_cond",
        "real_linear_xva": "Real_Linear_xva/Real_Linear_xva.csv",
        "pendulum_h_1": "Ideal_Pendulum/Ideal_Pendulum.csv"
    }.items()
}

systems = {**auto.systems, **nauto.systems, **ssm.systems, **cs.systems}
emulators = systems

