#!/usr/bin/python3
# -*- coding: utf-8 -*-

'''Pychemqt, Chemical Engineering Process simulator
Copyright (C) 2016, Juan José Gómez Romera <jjgomera@gmail.com>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.'''



###############################################################################
# Module with configuration tools
#   - getComponents: Get component list from project
#   - getMainWindowConfig: Return config of current project
#   - Entity: General class for model object
#   - Fluid: dict class wiih custom properties

#   Variables:
#   - conf_dir: User configuration path
#   - Preferences: ConfigParser instance with pychemqt preferences
###############################################################################

import os

# TODO: Delete when it isn´t necessary debug
#os.environ["pychemqt"]="/home/jjgomera/pychemqt/"
#os.environ["freesteam"]="False"
#os.environ["oasa"]="False"
#os.environ["CoolProp"]="True"
#os.environ["refprop"]="False"
#os.environ["ezodf"]="False"
#os.environ["openpyxl"]="False"
#os.environ["xlwt"]="False"
#os.environ["icu"]="True"


from configparser import ConfigParser
from PyQt5 import QtWidgets
from lib.sql import databank


conf_dir = os.path.expanduser('~') + os.sep+".pychemqt"+os.sep
QTSETTING_FILE = os.path.expanduser('~') + os.sep +\
    ".config/pychemqt/pychemqt.conf"
Preferences = ConfigParser()
Preferences.read(conf_dir+"pychemqtrc")
# FIXME: This instance is not update when preferences are changed

global currentConfig
currentConfig = ConfigParser()
currentConfig.read(conf_dir+"pychemqtrc_temporal")


def getComponents(solidos=False, config=None, name=True):
    """
    Return components or current project
        solidos: boolean if return solids components
        config: we can input the config to extract
        name: boolean to return too name and molecular weight of component
    """
    if not config:
        config = getMainWindowConfig()
    if solidos:
        indices = config.get("Components", "Solids")
        if not isinstance(indices, list):
            indices = eval(indices)
    else:
        indices = config.get("Components", "Components")
        if not isinstance(indices, list):
            indices = eval(indices)

    if name:
        nombres = []
        M = []
        for componente in indices:
            databank.execute("select nombre, peso_molecular from compuestos \
where id == %s" % str(componente))
            texto = databank.fetchone()
            nombres.append(texto[0])
            M.append(texto[1])
        return indices, nombres, M
    else:
        return indices


def getMainWindowConfig():
    """Return config of current project"""
    return currentConfig


def setMainWindowConfig(config=None):
    """Return config of current project"""
    global currentConfig
    if config:
        currentConfig = config
        return
    else:
        widget = QtWidgets.QApplication.activeWindow()
        if isinstance(widget, QtWidgets.QMainWindow) and \
           widget.__class__.__name__ == "UI_pychemqt":
            currentConfig = widget.currentConfig
        else:
            lista = QtWidgets.QApplication.topLevelWidgets()
            for widget in lista:
                if isinstance(widget, QtWidgets.QMainWindow) and \
                   widget.__class__.__name__ == "UI_pychemqt":
                    currentConfig = widget.currentConfig
                    break


class Entity(object):
    """
    General class for model object, with basic functionality:
        -clear object
        -definition of boolean characteristic of object
        -input used for definition
        -note properties with description
        -save/load from file
        -properties for report, tooltip

    Child class include:
        -Corriente, Mezcla, Solids
        -equipment
    """
    _bool = False
    kwargs_forbidden = ["entrada"]
    notas = ""
    notasPlain = ""

    def __init__(self, **kwargs):
        """
        Class constructor, copy kwargs for child class, it can be customize
        for child class to add functionality
        """
        self.kwargs = self.__class__.kwargs.copy()

        # Values defined as integer Entrada_con_unidades return as float
        # and it must be corrected
        self.kwargsInteger = []
        for key, value in self.kwargs.items():
            if isinstance(value, int):
                self.kwargsInteger.append(key)

        if kwargs:
            self.__call__(**kwargs)

    def __call__(self, **kwargs):
        """
        Add callable functionality, so it can be possible add kwargs,
        advanced functionality can be added in subclass"""
        self._oldkwargs = self.kwargs.copy()
        self.cleanOldValues(**kwargs)
        self._bool = True
        txt = kwargs.get("notas", "")
        if txt:
            self.notas = txt
            self.notasPlain = txt

        for key in self.kwargsInteger:
            if key not in self.kwargs_forbidden:
                self.kwargs[key] = int(self.kwargs[key])

    def cleanOldValues(self, **kwargs):
        """Update kwargs with new input kwargs, defined in child class,
        here can be implemented kwarg incompatibiity input and more"""
        self.kwargs.update(kwargs)

    def clear(self):
        """Clear entity and stay as new instance"""
        self.kwargs = self.__class__.kwargs
        self.__dict__.clear()
        self._bool = False

    def __bool__(self):
        return self._bool

    def show(self):
        """General function to show entity properties as key: value text"""
        for key in sorted(self.__dict__):
            print(key, ": ", self.__dict__[key])

    def setNotas(self, html, txt):
        self.notas = html
        self.notasPlain = txt
        if html:
            self._bool = True

    @property
    def numInputs(self):
        """Input count in kwargs"""
        count = 0
        for key, value in self.kwargs.items():
            if key not in self.kwargs_forbidden and value:
                count += 1
        return count

    # Read-Write to file
    def writeToStream(self, stream):
        """Save kwargs properties of entity to file"""
        stream.writeInt32(self.numInputs)
        for key, value in self.kwargs.items():
            if key not in self.kwargs_forbidden and value:
                stream.writeString(key.encode())
                if isinstance(value, float):
                    stream.writeFloat(value)
                elif isinstance(value, int):
                    stream.writeInt32(value)
                elif isinstance(value, str):
                    stream.writeString(value.encode())
                elif isinstance(value, list):
                    self.writeListtoStream(stream, key, value)
        # Write state
        stream.writeInt32(self.status)
        stream.writeString(self.msg.encode())
        stream.writeBool(self._bool)
        if self.status:
            self.writeStatetoStream(stream)

    def writeListtoStream(self, stream, key, value):
        """Write list to file, Customize in entities with complex list"""
        stream.writeInt32(len(value))
        for val in value:
            stream.writeFloat(val)

    def readFromStream(self, stream, run=True):
        """Read entity from file
        run: opcional parameter if we not want run it"""
        for i in range(stream.readInt32()):
            key = stream.readString().decode("utf-8")
            if isinstance(self.kwargs[key], float):
                valor = stream.readFloat()
            elif isinstance(self.kwargs[key], int):
                valor = stream.readInt32()
            elif isinstance(self.kwargs[key], str):
                valor = stream.readString().decode("utf-8")
            elif isinstance(self.kwargs[key], list):
                valor = self.readListFromStream(stream, key)
            self.kwargs[key] = valor
        # Read state
        self.status = stream.readInt32()
        self.msg = stream.readString().decode("utf-8")
        self._bool = stream.readBool()
        if self.status:
            self.readStatefromStream(stream)

#        if run:
#            self.__call__()
#            print(self)

    def readListFromStream(self, stream, key):
        """Read list from file, customize in entities with complex list"""
        valor = []
        for i in range(stream.readInt32()):
            valor.append(stream.readFloat())
        return valor

    def writeStatetoStream(self, stream):
        pass

    def readStatefromStream(self, stream):
        pass

    # Properties
    @classmethod
    def propertiesNames(cls):
        """List with properties availables for show in poput"""
        return []

    def properties(self):
        lista = []
        for name, attr, unit in self.propertiesNames():
            prop = self._prop(attr)
            if isinstance(prop, list):
                if unit == str:
                    lista.append((prop, name))
                elif unit is None:
                    lista.append((["" for f in prop], name))
                else:
                    lista.append(([f.str for f in prop], name))
            elif unit == str:
                lista.append((prop, name, 0))
            elif unit == int:
                lista.append((str(prop), name, 1))
            else:
                lista.append((prop.str, name, 1))
        return lista

    def _prop(self, attr):
        if attr == "className":
            prop = self.__class__.__name__
        elif attr == "notasPlain":
            prop = self.notasPlain
        elif type(attr) == tuple:
            prop = self.__getattribute__(attr[0])[self.kwargs[attr[1]]]
        elif attr in self.__dict__:
            prop = self.__getattribute__(attr)
        elif attr in self.kwargs and self.kwargs[attr]:
            prop = self.kwargs[attr]
        return prop

    def propertiesListTitle(self, index):
        """Define titles for list properties in popup"""
        pass

    def propertiesTitle(self):
        return [prop[0] for prop in self.propertiesNames()]

    def propertiesAttribute(self):
        return [prop[1] for prop in self.propertiesNames()]

    def propertiesUnit(self):
        return [prop[2] for prop in self.propertiesNames()]

    def popup(self, preferences, exception=[]):
        """
        Return a list with properties of entity to show in a puput
        preferences: ConfigParser instance with selected properties to show"""
        txt = []
        propiedades = self.properties()
        for i in eval(preferences.get("TooltipEntity",
                                      self.__class__.__name__)):
            if isinstance(propiedades[i][0], list):
                txt.append((propiedades[i][1], "", 0))
                title = self.propertiesListTitle(i)
                for name, value in zip(title, propiedades[i][0]):
                    txt.append(("%s\t%s" % (name, value), "", 1))
            else:
                txt.append(propiedades[i])
        return txt
