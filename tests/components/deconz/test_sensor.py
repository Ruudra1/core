"""deCONZ sensor platform tests."""
from copy import deepcopy

from homeassistant.components import deconz
import homeassistant.components.sensor as sensor
from homeassistant.const import (
    DEVICE_CLASS_BATTERY,
    DEVICE_CLASS_ILLUMINANCE,
    DEVICE_CLASS_POWER,
)
from homeassistant.setup import async_setup_component

from .test_gateway import DECONZ_WEB_REQUEST, setup_deconz_integration

SENSORS = {
    "1": {
        "id": "Light sensor id",
        "name": "Light level sensor",
        "type": "ZHALightLevel",
        "state": {"lightlevel": 30000, "dark": False},
        "config": {"on": True, "reachable": True, "temperature": 10},
        "uniqueid": "00:00:00:00:00:00:00:00-00",
    },
    "2": {
        "id": "Presence sensor id",
        "name": "Presence sensor",
        "type": "ZHAPresence",
        "state": {"presence": False},
        "config": {},
        "uniqueid": "00:00:00:00:00:00:00:01-00",
    },
    "3": {
        "id": "Switch 1 id",
        "name": "Switch 1",
        "type": "ZHASwitch",
        "state": {"buttonevent": 1000},
        "config": {},
        "uniqueid": "00:00:00:00:00:00:00:02-00",
    },
    "4": {
        "id": "Switch 2 id",
        "name": "Switch 2",
        "type": "ZHASwitch",
        "state": {"buttonevent": 1000},
        "config": {"battery": 100},
        "uniqueid": "00:00:00:00:00:00:00:03-00",
    },
    "5": {
        "id": "Daylight sensor id",
        "name": "Daylight sensor",
        "type": "Daylight",
        "state": {"daylight": True, "status": 130},
        "config": {},
        "uniqueid": "00:00:00:00:00:00:00:04-00",
    },
    "6": {
        "id": "Power sensor id",
        "name": "Power sensor",
        "type": "ZHAPower",
        "state": {"current": 2, "power": 6, "voltage": 3},
        "config": {"reachable": True},
        "uniqueid": "00:00:00:00:00:00:00:05-00",
    },
    "7": {
        "id": "Consumption id",
        "name": "Consumption sensor",
        "type": "ZHAConsumption",
        "state": {"consumption": 2, "power": 6},
        "config": {"reachable": True},
        "uniqueid": "00:00:00:00:00:00:00:06-00",
    },
    "8": {
        "id": "CLIP light sensor id",
        "name": "CLIP light level sensor",
        "type": "CLIPLightLevel",
        "state": {"lightlevel": 30000},
        "config": {"reachable": True},
        "uniqueid": "00:00:00:00:00:00:00:07-00",
    },
}


async def test_platform_manually_configured(hass):
    """Test that we do not discover anything or try to set up a gateway."""
    assert (
        await async_setup_component(
            hass, sensor.DOMAIN, {"sensor": {"platform": deconz.DOMAIN}}
        )
        is True
    )
    assert deconz.DOMAIN not in hass.data


async def test_no_sensors(hass):
    """Test that no sensors in deconz results in no sensor entities."""
    await setup_deconz_integration(hass)
    assert len(hass.states.async_all()) == 0


async def test_sensors(hass):
    """Test successful creation of sensor entities."""
    data = deepcopy(DECONZ_WEB_REQUEST)
    data["sensors"] = deepcopy(SENSORS)
    gateway = await setup_deconz_integration(hass, get_state_response=data)

    assert len(hass.states.async_all()) == 5

    light_level_sensor = hass.states.get("sensor.light_level_sensor")
    assert light_level_sensor.state == "999.8"
    assert light_level_sensor.attributes["device_class"] == DEVICE_CLASS_ILLUMINANCE

    assert hass.states.get("sensor.presence_sensor") is None
    assert hass.states.get("sensor.switch_1") is None
    assert hass.states.get("sensor.switch_1_battery_level") is None
    assert hass.states.get("sensor.switch_2") is None

    switch_2_battery_level = hass.states.get("sensor.switch_2_battery_level")
    assert switch_2_battery_level.state == "100"
    assert switch_2_battery_level.attributes["device_class"] == DEVICE_CLASS_BATTERY

    assert hass.states.get("sensor.daylight_sensor") is None

    power_sensor = hass.states.get("sensor.power_sensor")
    assert power_sensor.state == "6"
    assert power_sensor.attributes["device_class"] == DEVICE_CLASS_POWER

    consumption_sensor = hass.states.get("sensor.consumption_sensor")
    assert consumption_sensor.state == "0.002"
    assert "device_class" not in consumption_sensor.attributes

    assert hass.states.get("sensor.clip_light_level_sensor") is None

    # Event signals new light level

    state_changed_event = {
        "t": "event",
        "e": "changed",
        "r": "sensors",
        "id": "1",
        "state": {"lightlevel": 2000},
    }
    gateway.api.event_handler(state_changed_event)

    assert hass.states.get("sensor.light_level_sensor").state == "1.6"

    # Event signals new battery level

    state_changed_event = {
        "t": "event",
        "e": "changed",
        "r": "sensors",
        "id": "4",
        "config": {"battery": 75},
    }
    gateway.api.event_handler(state_changed_event)
    await hass.async_block_till_done()

    assert hass.states.get("sensor.switch_2_battery_level").state == "75"

    await gateway.async_reset()

    assert len(hass.states.async_all()) == 0


async def test_allow_clip_sensors(hass):
    """Test that CLIP sensors can be allowed."""
    data = deepcopy(DECONZ_WEB_REQUEST)
    data["sensors"] = deepcopy(SENSORS)
    gateway = await setup_deconz_integration(
        hass,
        options={deconz.gateway.CONF_ALLOW_CLIP_SENSOR: True},
        get_state_response=data,
    )

    assert len(hass.states.async_all()) == 6
    assert hass.states.get("sensor.clip_light_level_sensor").state == "999.8"

    # Disallow clip sensors

    hass.config_entries.async_update_entry(
        gateway.config_entry, options={deconz.gateway.CONF_ALLOW_CLIP_SENSOR: False}
    )
    await hass.async_block_till_done()

    assert len(hass.states.async_all()) == 5
    assert hass.states.get("sensor.clip_light_level_sensor") is None

    # Allow clip sensors

    hass.config_entries.async_update_entry(
        gateway.config_entry, options={deconz.gateway.CONF_ALLOW_CLIP_SENSOR: True}
    )
    await hass.async_block_till_done()

    assert len(hass.states.async_all()) == 6
    assert hass.states.get("sensor.clip_light_level_sensor")


async def test_add_new_sensor(hass):
    """Test that adding a new sensor works."""
    gateway = await setup_deconz_integration(hass)
    assert len(hass.states.async_all()) == 0

    state_added_event = {
        "t": "event",
        "e": "added",
        "r": "sensors",
        "id": "1",
        "sensor": deepcopy(SENSORS["1"]),
    }
    gateway.api.event_handler(state_added_event)
    await hass.async_block_till_done()

    assert len(hass.states.async_all()) == 1
    assert hass.states.get("sensor.light_level_sensor").state == "999.8"


async def test_add_battery_later(hass):
    """Test that a sensor without an initial battery state creates a battery sensor once state exist."""
    data = deepcopy(DECONZ_WEB_REQUEST)
    data["sensors"] = {"1": deepcopy(SENSORS["3"])}
    gateway = await setup_deconz_integration(hass, get_state_response=data)
    remote = gateway.api.sensors["1"]

    assert len(hass.states.async_all()) == 0
    assert len(gateway.events) == 1
    assert len(remote._callbacks) == 2  # Event and battery tracker

    remote.update({"config": {"battery": 50}})
    await hass.async_block_till_done()

    assert len(hass.states.async_all()) == 1
    assert len(gateway.events) == 1
    assert len(remote._callbacks) == 2  # Event and battery entity

    assert hass.states.get("sensor.switch_1_battery_level")
