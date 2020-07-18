#!/usr/bin/python3
#
# Copyright (C) 2019 Google Inc.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import plspm.config as c, pandas as pd, numpy.testing as npt
from plspm.weights import WeightsCalculatorFactory
from plspm.scale import Scale
from typing import Tuple

class Estimator:
    def __init__(self, config: c.Config):
        self.__config = config
        self.__hoc_path_first_stage = self.hoc_path_first_stage()

    def estimate(self, calculator: WeightsCalculatorFactory, data: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        hocs = self.__config.hoc()

        if hocs is not None:
            path = self.__hoc_path_first_stage

        treated_data = self.__config.treat(data)
        final_data, scores, weights = calculator.calculate(treated_data, path)

        # If we have higher order constructs, re-estimate the model using the scores of the constituent LVs of the HOC
        # generated by the first round of estimation as the HOC's MVs.
        if hocs is not None:
            scale = None if self.__config.metric() else Scale.NUM
            for hoc in hocs:
                new_mvs = []
                for lv in hocs[hoc]:
                    mv_new = lv
                    treated_data[mv_new] = scores[lv]
                    new_mvs.append(c.MV(mv_new, scale))
                self.__config.add_lv(hoc, self.__config.mode(hoc), *new_mvs)
            final_data, scores, weights = calculator.calculate(treated_data, self.__config.path())

        return final_data, scores, weights

    def hoc_path_first_stage(self) -> pd.DataFrame:
        # For first pass, for HOCs we'll create paths from each and for each exogenous LV to the HOC's constituent LVs,
        # and from each consituent LV to the endogenous LVs.
        path = self.__config.path()
        for hoc, lvs in self.__config.hoc().items():
            structure = c.Structure(path)
            exogenous = path.loc[hoc]
            endogenous = path.loc[:,hoc]
            # structure.add_path(lvs, [hoc])
            for lv in list(exogenous[exogenous == 1].index):
                structure.add_path([lv], lvs)
            for lv in list(endogenous[endogenous == 1].index):
                structure.add_path(lvs, [lv])
            path = structure.path().drop(hoc).drop(hoc,axis = 1)
        return path