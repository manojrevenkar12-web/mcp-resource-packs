import pytest

from resourcepacks.settings import load
from resourcepacks.world.sim import World


@pytest.fixture(scope="session")
def cfg():
    return load("packs")


@pytest.fixture(scope="session")
def world():
    return World(load("world"))
