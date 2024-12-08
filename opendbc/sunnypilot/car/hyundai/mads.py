from collections import namedtuple

from opendbc.car import DT_CTRL, structs
from opendbc.car.hyundai.values import CAR

from opendbc.sunnypilot import SunnypilotParamFlags
from opendbc.sunnypilot.mads_base import MadsCarStateBase

ButtonType = structs.CarState.ButtonEvent.Type

MadsDataSP = namedtuple("MadsDataSP",
                        ["enable_mads", "lat_active", "disengaging", "paused"])


class MadsCarController:
  def __init__(self):
    super().__init__()
    self.mads = MadsDataSP(False, False, False, False)

    self.lat_disengage_blink = 0
    self.lat_disengage_init = False
    self.prev_lat_active = False

    self.lkas_icon = 0
    self.lfa_icon = 0

  # display LFA "white_wheel" and LKAS "White car + lanes" when not CC.latActive
  def mads_status_update(self, CC: structs.CarControl, frame: int) -> MadsDataSP:
    enable_mads = CC.sunnypilotParams & SunnypilotParamFlags.ENABLE_MADS

    if CC.latActive:
      self.lat_disengage_init = False
    elif self.prev_lat_active:
      self.lat_disengage_init = True

    if not self.lat_disengage_init:
      self.lat_disengage_blink = frame

    paused = CC.madsEnabled and not CC.latActive
    disengaging = (frame - self.lat_disengage_blink) * DT_CTRL < 1.0 if self.lat_disengage_init else False

    self.prev_lat_active = CC.latActive

    return MadsDataSP(enable_mads, CC.latActive, disengaging, paused)

  def create_lkas_icon(self, CP: structs.CarParams, enabled: bool) -> int:
    if self.mads.enable_mads:
      lkas_icon = 2 if self.mads.lat_active else 3 if self.mads.disengaging else 1 if self.mads.paused else 0
    else:
      lkas_icon = 2 if enabled else 1

    # Override common signals for KIA_OPTIMA_G4 and KIA_OPTIMA_G4_FL
    if CP.carFingerprint in (CAR.KIA_OPTIMA_G4, CAR.KIA_OPTIMA_G4_FL):
      lkas_icon = 3 if (self.mads.lat_active if self.mads.enable_mads else enabled) else 1

    return lkas_icon

  def create_lfa_icon(self, enabled: bool) -> int:
    if self.mads.enable_mads:
      lfa_icon = 2 if self.mads.lat_active else 3 if self.mads.disengaging else 1 if self.mads.paused else 0
    else:
      lfa_icon = 2 if enabled else 0

    return lfa_icon

  def update(self, CP: structs.CarParams, CC: structs.CarControl, frame: int):
    self.mads = self.mads_status_update(CC, frame)
    self.lkas_icon = self.create_lkas_icon(CP, CC.enabled)
    self.lfa_icon = self.create_lfa_icon(CC.enabled)


class MadsCarState(MadsCarStateBase):
  def __init__(self):
    super().__init__()
    self.main_cruise_enabled: bool = False

  def get_main_cruise(self, ret: structs.CarState) -> bool:
    if any(be.type == ButtonType.mainCruise and not be.pressed for be in ret.buttonEvents):
      self.main_cruise_enabled = not self.main_cruise_enabled

    return self.main_cruise_enabled if ret.cruiseState.available else False
