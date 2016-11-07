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
# Module to define common graphics widget for pychemqt
#   -Status: Label with status (for equipment, stream)
#   -Entrada_con_unidades: Composite widget for unit values for input/view
#   -Tabla: Custom tablewidget tablewidget with added functionality
#   -ClickableLabel: Label with custom clicked signal
#   -ColorSelector: Composite widget for colour definition
#   -DragButton: Button with drag & drop support
#   -TreeEquipment:
#   -

#   -TabWidget: Custom tabwidget to show a message in mainwindow when no
#       project is loaded
###############################################################################


from configparser import ConfigParser
import os
import sys

from PyQt5 import QtCore, QtGui, QtWidgets

from lib import config
from lib.utilities import representacion
from lib.corriente import Corriente
from tools.UI_unitConverter import UI_conversorUnidades, moneda
from UI.delegate import CellEditor


class Status(QtWidgets.QLabel):
    """Widget with status of dialog, equipment, stream, project, ..."""
    status = (
        (0, QtWidgets.QApplication.translate("pychemqt", "Underspecified"),
         "yellow"),
        (1, QtWidgets.QApplication.translate("pychemqt", "Solved"), "green"),
        (2, QtWidgets.QApplication.translate("pychemqt", "Ignored"),
         "Light gray"),
        (3, QtWidgets.QApplication.translate("pychemqt", "Warning"), "green"),
        (4, QtWidgets.QApplication.translate("pychemqt", "Calculating..."),
         "Cyan"),
        (5, QtWidgets.QApplication.translate("pychemqt", "Error"),  "red"))

    def __init__(self, state=0, text="", parent=None):
        """
        state:
            0   -   Not solved
            1   -   OK
            2   -   Ignore
            3   -   Warning (Recommend: Use text parameter to explain)
            4   -   Calculating
            5   -   Error
        """
        super(Status, self).__init__(parent)
        self.setState(state)
        self.setAlignment(QtCore.Qt.AlignCenter)
        self.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.setFrameShape(QtWidgets.QFrame.Panel)
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding,
                           QtWidgets.QSizePolicy.Preferred)
        self.oldState = 0
        self.oldText = ""

    def setState(self, state, text=""):
        """Change the state"""

        if state == 2:
            self.oldState = self.state
            oldtext = self.text().split(": ")
            if len(oldtext) == 1:
                self.oldText = ""
            else:
                self.oldText = oldtext[1:].join(": ")
        if text:
            self.setText(self.status[state][1]+": "+text)
        else:
            self.setText(self.status[state][1])
        self.setStyleSheet(
            "QLabel { background-color: %s}" % self.status[state][2])
        QtWidgets.QApplication.processEvents()
        self.state = state

    def restaurar(self):
        """Restore old stade"""
        self.setState(self.oldState, self.oldText)


class Entrada_con_unidades(QtWidgets.QWidget):
    """Customized widget with unit functionality"""

    valueChanged = QtCore.pyqtSignal(float)

    def __init__(self, unidad, UIconfig=None, retornar=True, readOnly=False,
                 boton=True, texto=True, textounidad="", title="", value=None,
                 start=0, max=float("inf"), min=0, decimales=4, tolerancia=4,
                 parent=None, width=85, resaltado=False, spinbox=False,
                 suffix="", step=0.01, colorReadOnly=None, colorResaltado=None,
                 frame=True, showNull=False):
        """
        Units:
            unidad: The unit (lib/unidades class) to use, mandatory
            UIconfig: Magnitud necessary if the main unit have several meaning
            title: Update unit title property
            retornar: Boolean to let or avoid the conversion window update
                the value of widget
            value: Inicial value of widget
            max: Maximum value for widget
            min: Minimum value for widget
            decimales: Decimal number count to show of value
            tolerancia: Value of exponent over than to use exponential notation
        UI:
            readOnly: Boolean, set widget readOnly property
            frame: Boolean, show the frame of widget or not
            width: Width of value widget
            boton: Boolean, show or not the button for unit conversion dialog
            texto: Boolean, show the unit text at right of value
            textounidad: Alternate text to show as unit text
            suffix: Text added to value in value representation
            showNull: Boolean, show value if it's 0
            resaltado: Boolean, use base color in widget
            colorResaltado: Color to use as base color if value
            colorReadOnly: Color to use is the widget is readOnly
        Spinbox functionality:
            spinbox: boolean to specified a QSpinbox use, with mouse response
            start: initial value for spinbox mouse interaction
            step: value of step at mouse spingox interaction
        """
        super(Entrada_con_unidades, self).__init__(parent)
        self.resize(self.minimumSize())
        self.unidad = unidad

        if title:
            self.unidad.__title__ = title
        if unidad == float or unidad == int:
            self.magnitud = None
        else:
            self.magnitud = unidad.__name__
        if unidad == int and spinbox and step == 0.01:
            step = 1
        self.decimales = decimales
        self.tolerancia = tolerancia
        self.step = step
        self.spinbox = spinbox
        self.max = max
        self.suffix = suffix
        self.min = min
        self.start = start
        self.textounidad = textounidad
        self.boton = boton
        self.resaltado = resaltado
        self.showNull = showNull

        Config = ConfigParser()
        Config.read(config.conf_dir+"pychemqtrc")
        if colorReadOnly:
            self.colorReadOnly = colorReadOnly
        else:
            self.colorReadOnly = QtGui.QColor(
                Config.get("General", 'Color_ReadOnly'))
        if colorResaltado:
            self.colorResaltado = colorResaltado
        else:
            self.colorResaltado = QtGui.QColor(
                Config.get("General", 'Color_Resaltado'))

        if UIconfig:
            self.UIconfig = UIconfig
        else:
            self.UIconfig = self.magnitud
        self.retornar = retornar
        layout = QtWidgets.QGridLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.entrada = QtWidgets.QLineEdit()
        self.entrada.setFixedSize(width, 24)
        self.entrada.editingFinished.connect(self.entrada_editingFinished)
        self.entrada.setAlignment(
            QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        if unidad == int:
            if max == float("inf"):
                max = 1000000000
            validator = QtGui.QIntValidator(min, max, self)
        else:
            validator = QtGui.QDoubleValidator(min, max, decimales, self)
            locale = QtCore.QLocale("en")
            validator.setLocale(locale)
        self.entrada.setValidator(validator)
        self.setReadOnly(readOnly)
        self.setRetornar(self.retornar)
        self.setFrame(frame)
        layout.addWidget(self.entrada, 0, 1, 1, 3)

        if value is None:
            self.value = self.unidad(0)
        else:
            self.setValue(value)
        if self.magnitud:
            if boton:
                self.unidades = QtWidgets.QPushButton(".")
                self.unidades.setFixedSize(12, 24)
                self.unidades.setVisible(False)
                self.unidades.clicked.connect(self.unidades_clicked)
                layout.addWidget(self.unidades, 0, 1)

        if boton:
            self.botonClear = QtWidgets.QPushButton(QtGui.QIcon(QtGui.QPixmap(
                os.environ["pychemqt"] +
                os.path.join("images", "button", "editDelete.png"))), "")
            self.botonClear.setFixedSize(12, 24)
            self.botonClear.setVisible(False)
            self.botonClear.clicked.connect(self.clear)
            layout.addWidget(self.botonClear, 0, 3)

        if texto:
            self.texto = QtWidgets.QLabel()
            self.texto.setAlignment(QtCore.Qt.AlignVCenter)
            self.texto.setIndent(5)
            txt = ""
            if self.UIconfig:
                txt += self.value.text(self.UIconfig)
            if textounidad:
                txt += textounidad
            self.texto.setText(txt)
            layout.addWidget(self.texto, 0, 4)

        layout.addItem(QtWidgets.QSpacerItem(
            0, 0, QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Fixed), 0, 5)
        self.setResaltado(resaltado)

    def unidades_clicked(self):
        """Show the unit converter dialog"""
        if self.magnitud == "Currency":
            dialog = moneda(self.value)
        else:
            dialog = UI_conversorUnidades(self.unidad, self.value)

        if dialog.exec_() and self.retornar:
            # Change the value if change and retornar if active
            self.entrada.setText(
                representacion(dialog.value.config(self.UIconfig))+self.suffix)
            oldvalue = self.value
            self.value = dialog.value
            if oldvalue != self.value:
                self.valueChanged.emit(self.value)

    def entrada_editingFinished(self):
        """Change the value at finish of edit"""
        if not self.readOnly:
            # Filter suffix and fix bad numeric , interpretation
            if self.suffix:
                txt = self.entrada.text().split(self.suffix).replace(',', '.')
            else:
                txt = self.entrada.text().replace(',', '.')
            if self.unidad != int:
                self.entrada.setText(
                    representacion(float(txt), decimales=self.decimales,
                                   tol=self.tolerancia)+self.suffix)
            oldvalue = self.value
            if self.magnitud:
                self.value = self.unidad(
                    float(txt), "conf", magnitud=self.UIconfig)
            else:
                self.value = self.unidad(txt)
            if self.value != oldvalue:
                self.valueChanged.emit(self.value)
                self.setToolTip()

    def clear(self):
        """Clear value"""
        self.entrada.setText("")
        self.value = None

    def setResaltado(self, bool):
        self.resaltado = bool
        paleta = QtGui.QPalette()
        if bool:
            paleta.setColor(
                QtGui.QPalette.Base, QtGui.QColor(self.colorResaltado))
        elif self.readOnly:
            paleta.setColor(
                QtGui.QPalette.Base, QtGui.QColor(self.colorReadOnly))
        else:
            paleta.setColor(QtGui.QPalette.Base, QtGui.QColor("white"))
        self.entrada.setPalette(paleta)

    def setReadOnly(self, readOnly):
        self.entrada.setReadOnly(readOnly)
        self.readOnly = readOnly
        self.setResaltado(self.resaltado)

    def setNotReadOnly(self, editable):
        self.setReadOnly(not editable)

    def setRetornar(self, retornar):
        self.retornar = retornar

    def setValue(self, value):
        self.value = self.unidad(value)
        if value or self.showNull:
            if self.magnitud:
                self.entrada.setText(
                    self.value.format(magnitud=self.UIconfig)+self.suffix)
            elif self.unidad == float:
                self.entrada.setText(
                    representacion(self.value, decimales=self.decimales,
                                   tol=self.tolerancia)+self.suffix)
            else:
                self.entrada.setText(str(self.value)+self.suffix)
            self.setToolTip()

    def setFrame(self, frame):
        self.entrada.setFrame(frame)
        self.frame = frame

    def setToolTip(self):
        """Define the tooltip with the values in confguration"""
        Preferences = ConfigParser()
        Preferences.read(config.conf_dir+"pychemqtrc")
        if Preferences.getboolean("Tooltip", "Show"):
            Config = ConfigParser()
            Config.read(config.conf_dir+"pychemqtrc")
            try:
                lista = eval(Config.get('Tooltip', self.magnitud))
            except:
                lista = []
            if len(lista) > 0:
                valores = []
                for i in lista:
                    valores.append(representacion(
                        self.value.__getattribute__(self.value.__units__[i]),
                        self.decimales, self.tolerancia) + " " +
                        self.value.__text__[i])
                self.entrada.setToolTip(os.linesep.join(valores))

    def keyPressEvent(self, e):
        """Manage the key press to emulate a QSpinbox"""
        if not self.readOnly:
            if e.key() in [QtCore.Qt.Key_Insert, QtCore.Qt.Key_Backspace]:
                self.clear()
            if self.spinbox:
                if not self.value:
                    self.value = self.start
                if e.key() == QtCore.Qt.Key_Up:
                    valor = self.value+self.step
                    if valor > self.max:
                        self.setValue(self.max)
                    else:
                        self.setValue(valor)
                elif e.key() == QtCore.Qt.Key_Down:
                    valor = self.value-self.step
                    if valor < self.min:
                        self.setValue(self.min)
                    else:
                        self.setValue(valor)
                self.valueChanged.emit(self.value)

    def enterEvent(self, event):
        """When mouse enter in widget show the unidades and clear button, and
        add margin to let space to clear button"""
        if self.magnitud and self.boton:
            self.unidades.setVisible(True)
        if self.value and self.boton and not self.readOnly:
            self.botonClear.setVisible(True)
            self.entrada.setTextMargins(0, 0, 10, 0)

    def leaveEvent(self, event):
        """When mouse leave the widget undo the enterEvent actions"""
        if self.magnitud and self.boton:
            self.unidades.setVisible(False)
        if self.value and self.boton and not self.readOnly:
            self.botonClear.setVisible(False)
            self.entrada.setTextMargins(0, 0, 0, 0)


class Tabla(QtWidgets.QTableWidget):
    """Clase que genera tablas personalizadas para entrada de datos"""
    editingFinished = QtCore.pyqtSignal()
    rowFinished = QtCore.pyqtSignal(list)

    def __init__(self, columnas=0, horizontalHeader=None, verticalHeaderLabels=None,
                 verticalHeader=True, filas=0, stretch=True, verticalOffset=0,
                 dinamica=False, external=False, orientacion=QtCore.Qt.AlignRight,
                 verticalHeaderModel="", readOnly=False, columnReadOnly=None,
                 num=True, delegateforRow=None, parent=None):
        """
        columnas: número de columnas
        horizontalHeader: texto de título de columnas
        verticalHeaderLabels: texto de título de filas
        verticalHeader: boolean que indica si será visible el verticalHeader
        filas: número de filas iniciales
        stretch: indica si la ultima columla coge todo el espacio disponible
        verticalOffset: indice que indica las filas que no se usaran para el rellenado (usadas por widget por ejemplo)
        verticalHeaderModel: Texto que se usa en el caso que la tabla sea dinamica y el verticalHeader visible
        """
        QtWidgets.QTableWidget.__init__(self, parent)
        self.columnas=columnas
        self.encabezadoHorizontal=horizontalHeader
        self.encabezadoVertical=verticalHeaderLabels
        self.filas=filas+verticalOffset
        self.verticalOffset=verticalOffset
        self.orientacion=orientacion
        self.verticalHeaderBool=verticalHeader
        self.verticalHeaderModel=verticalHeaderModel
        self.readOnly=readOnly
        if columnReadOnly==None:
            self.columnReadOnly=[self.readOnly]*self.columnas
        else:
            self.columnReadOnly=columnReadOnly
        if dinamica and not external:
            self.cellChanged.connect(self.tabla_cellChanged)
        self.dinamica=dinamica
        self.external=external
        if num:
            self.setItemDelegate(CellEditor(self))
        self.delegateforRow=delegateforRow
        self.setColumnCount(self.columnas)
#        self.setAlternatingRowColors(True)
        self.setGridStyle(QtCore.Qt.DotLine)
        if readOnly:
            self.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        else:
            self.setEditTriggers(QtWidgets.QAbstractItemView.AllEditTriggers)
        self.horizontalHeader().setStretchLastSection(stretch)
        if not verticalHeader:
            self.verticalHeader().hide()
        if not horizontalHeader:
            self.horizontalHeader().hide()
        self.iniciar(self.filas)

    def setConnected(self):
        self.cellChanged.connect(self.tabla_cellChanged)
        self.dinamica=True
        if self.rowCount()==0:
            self.addRow()

    def iniciar(self, filas):
        for i in range(filas):
            self.addRow()
        if self.encabezadoHorizontal:
            for i, titulo in enumerate(self.encabezadoHorizontal):
                self.setHorizontalHeaderItem(i,QtWidgets.QTableWidgetItem(titulo))

    def addRow(self, data=None, index=None):
        if not data:
            data=[""]*self.columnas
        else:
            data=[representacion(i) for i in data]
        self.blockSignals(True)
        if index is not None:
            i = index
        else:
            i=self.rowCount()
        self.insertRow(i)
#        self.setRowCount(i+1)
        self.setRowHeight(i, 22)
        if self.delegateforRow:
            delegate=self.delegateforRow(self.parent())
            self.setItemDelegateForRow(i, delegate)

        Config=ConfigParser()
        Config.read(config.conf_dir+"pychemqtrc")
        for j in range(self.columnCount()):
            self.setItem(i, j, QtWidgets.QTableWidgetItem(data[j]))
            self.item(i, j).setTextAlignment(self.orientacion|QtCore.Qt.AlignVCenter)

            inactivo=QtGui.QColor(Config.get("General", 'Color_ReadOnly'))
            activo=QtGui.QColor(Config.get("General", 'Color_Resaltado'))
            if self.columnReadOnly[j]:
                flags=QtCore.Qt.ItemIsEnabled|QtCore.Qt.ItemIsSelectable
                self.item(i, j).setBackground(inactivo)
            else:
                flags=QtCore.Qt.ItemIsEditable|QtCore.Qt.ItemIsEnabled|QtCore.Qt.ItemIsSelectable
            self.item(i, j).setFlags(flags)

        if self.verticalHeaderBool:
            if self.encabezadoVertical:
                self.setVerticalHeaderItem(i,QtWidgets.QTableWidgetItem(self.encabezadoVertical[i]))
            elif self.verticalHeaderModel:
                self.setVerticalHeaderItem(i,QtWidgets.QTableWidgetItem(self.verticalHeaderModel+str(i)))
        self.blockSignals(False)

        if self.dinamica and self.rowCount()>1:
            columna=self.columnReadOnly.index(False)
            self.setCurrentCell(i, columna)

    def tabla_cellChanged(self,i,j):
        """Método que añade una nueva línea si es necesario"""
        self.blockSignals(True)
        nueva_linea=True
        col=0
        while col<self.columnas:
            if self.item(i,col).text()!="" or self.columnReadOnly[col]:
                col+=1
            else:
                nueva_linea=False
                break
        if nueva_linea and i==self.rowCount()-1:
            self.addRow()
            fila=self.getRow(i, num=False)
            self.rowFinished.emit(fila)
        self.blockSignals(False)


    def getValue(self, fila, columna):
        if self.item(fila, columna).text():
            return float(self.item(fila, columna).text())
        else:
            return None

    def setValue(self, fila, columna, value, orientacion=None):
        if not orientacion:
            orientacion=self.orientacion
        if isinstance(value, float) or isinstance(value, int):
            value=str(value)
        self.item(fila, columna).setText(value)
        self.item(fila, columna).setTextAlignment(orientacion|QtCore.Qt.AlignVCenter)

    def setColumn(self, columna, data, **format):
        while len(data)>self.rowCount()-self.verticalOffset:
            self.addRow()
        self.blockSignals(True)
        for fila, dato in enumerate(data):
            self.item(fila, columna).setText(representacion(dato, **format))
        self.blockSignals(False)

    def getColumn(self, columna, fill=True):
        lista=[]
        for i in range(self.verticalOffset, self.rowCount()):
            if self.item(i, columna).text():
                lista.append(float(self.item(i, columna).text()))
            elif fill:
                lista.append(0)
        return lista

    def getRow(self, fila, num=True):
        lista=[]
        if num:
            for i in range(self.columnCount()):
                lista.append(float(self.item(fila, i).text()))
        else:
            for i in range(self.columnCount()):
                lista.append(self.item(fila, i).text())
        return lista

    def getMatrix(self):
        matriz=[]
        for i in range(self.verticalOffset, self.rowCount()-1):
            lista=[]
            for j in range(self.columnCount()):
                lista.append(float(self.item(i, j).text()))
            matriz.append(lista)
        return matriz

    def setMatrix(self, matriz):
        self.blockSignals(True)

        for i in range(self.rowCount(), len(matriz)+self.verticalOffset):
            self.addRow()
        for fila in range(self.rowCount()-self.verticalOffset):
            for columna, dato in enumerate(matriz[fila]):
                self.setItem(fila+self.verticalOffset, columna, QtWidgets.QTableWidgetItem(representacion(dato)))
                self.item(fila+self.verticalOffset, columna).setTextAlignment(self.orientacion|QtCore.Qt.AlignVCenter)
        for i in range(self.verticalOffset, self.rowCount()):
            self.setRowHeight(i+self.verticalOffset, 20)
        self.editingFinished.emit()
        self.blockSignals(False)

    def clear(self, size=True):
        if size:
            self.setRowCount(1+self.verticalOffset)
        for fila in range(self.rowCount()):
            for columna in range(self.columnas):
                    self.item(fila+self.verticalOffset, columna).setText("")

    def setColumnReadOnly(self, column, bool):
        if bool:
            flags=QtCore.Qt.ItemIsEnabled|QtCore.Qt.ItemIsSelectable
        else:
            flags=QtCore.Qt.ItemIsEditable|QtCore.Qt.ItemIsEnabled|QtCore.Qt.ItemIsSelectable

        for i in range(self.rowCount()):
            self.item(i, column).setFlags(flags)

    def leaveEvent(self, event):
        if self.isEnabled():
            self.editingFinished.emit()

    def focusOutEvent(self, event):
        self.clearSelection()

    def keyPressEvent(self, e):
        if e.key()==QtCore.Qt.Key_Delete:
            for rango in self.selectedRanges():
                for i in range(rango.topRow(), rango.bottomRow()+1):
                    for j in range(rango.leftColumn(), rango.rightColumn()+1):
                        self.item(i, j).setText("")
            if self.dinamica:
                for i in sorted(self.selectionModel().selectedRows(), reverse=True):
                    self.removeRow(i.row())
                if self.rowCount()==0:
                    self.iniciar(1)
        elif e.key()==QtCore.Qt.Key_Down:
            self.setCurrentCell(self.currentRow()+1, self.currentColumn())
        elif e.key()==QtCore.Qt.Key_Up:
            self.setCurrentCell(self.currentRow()-1, self.currentColumn())


class ClickableLabel(QtWidgets.QLabel):
    """Custom QLabel with clicked functionality"""
    clicked = QtCore.pyqtSignal()

    def mousePressEvent(self, event):
        self.clicked.emit()


class ColorSelector(QtWidgets.QWidget):
    """Color selector widget"""
    valueChanged = QtCore.pyqtSignal('QString')

    def __init__(self, color="#ffffff", alpha=255, isAlpha=False, parent=None):
        super(ColorSelector, self).__init__(parent)

        lyt = QtWidgets.QHBoxLayout(self)
        lyt.setContentsMargins(0, 0, 0, 0)
        lyt.setSpacing(0)

        self.RGB = QtWidgets.QLineEdit()
        self.RGB.editingFinished.connect(self.rgbChanged)
        self.RGB.setFixedSize(80, 24)
        lyt.addWidget(self.RGB)
        self.button = QtWidgets.QToolButton()
        self.button.setFixedSize(24, 24)
        self.button.clicked.connect(self.ColorButtonClicked)
        lyt.addWidget(self.button)
        lyt.addItem(QtWidgets.QSpacerItem(
            20, 20, QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Fixed))

        if isAlpha:
            self.isAlpha = QtGui.QColor.HexArgb
        else:
            self.isAlpha = QtGui.QColor.HexRgb

        r = int(color[1:3], 16)
        g = int(color[3:5], 16)
        b = int(color[5:7], 16)
        color = QtGui.QColor(r, g, b, alpha)
        self.setColor(color)

    def setColor(self, color):
        """Set new color value and update text and button color"""
        # Accept color args as a #rgb string too
        if type(color) == str:
            color = QtGui.QColor(color)
        self.color = color
        self.button.setStyleSheet("background: %s;" % color.name(self.isAlpha))
        self.RGB.setText(color.name(self.isAlpha))

    def ColorButtonClicked(self):
        """Show the QColorDialog to let user choose new color"""
        dlg = QtWidgets.QColorDialog(self.color, self)
        if self.isAlpha:
            dlg.setOption(QtWidgets.QColorDialog.ShowAlphaChannel)
        if dlg.exec_():
            self.setColor(dlg.currentColor())
            self.valueChanged.emit(dlg.currentColor().name())

    def rgbChanged(self):
        """Let user define the color manually"""
        txt = self.RGB.text()

        # Avoid the editing finished with no changes
        if txt == self.color.name(self.isAlpha):
            return

        # Define the new color from text
        if self.isAlpha:
            alpha = int(txt[1:3], 16)
            r = int(txt[3:5], 16)
            g = int(txt[5:7], 16)
            b = int(txt[7:9], 16)
            color = QtGui.QColor(r, g, b, alpha)
        else:
            color = QtGui.QColor(txt)

        # Only accept new value if it's valid
        if color.isValid():
            self.setColor(color)
            self.valueChanged.emit(color.name(self.isAlpha))


class DragButton(QtWidgets.QToolButton):
    """Clase que define un botón especial que permite arrastrar"""

    def __init__(self, parent=None):
        super(DragButton, self).__init__(parent)

    def mouseMoveEvent(self, event):
        self.startDrag()
        QtWidgets.QToolButton.mouseMoveEvent(self, event)

    def startDrag(self):
        if self.icon().isNull():
            return
        data = QtCore.QByteArray()
        stream = QtCore.QDataStream(data, QtCore.QIODevice.WriteOnly)
        stream << self.icon()
        mimeData = QtCore.QMimeData()
        mimeData.setData("application/x-equipment", data)
        drag = QtGui.QDrag(self)
        drag.setMimeData(mimeData)
        pixmap = self.icon().pixmap(24, 24)
        drag.setHotSpot(QtCore.QPoint(12, 12))
        drag.setPixmap(pixmap)
        drag.start(QtCore.Qt.CopyAction)


class TreeEquipment(QtWidgets.QTreeWidget):

    def __init__(self, parent=None):
        super(TreeEquipment, self).__init__(parent)
        self.setIconSize(QtCore.QSize(30, 30))
        self.headerItem().setHidden(True)
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)

    def updateList(self, items):
        self.clear()
        self.Stream = QtWidgets.QTreeWidgetItem(self, 0)
        self.Stream.setText(
            0, QtWidgets.QApplication.translate("pychemqt", "Streams"))
        self.Stream.setExpanded(True)
        self.Equipment = QtWidgets.QTreeWidgetItem(self, 0)
        self.Equipment.setText(
            0, QtWidgets.QApplication.translate("pychemqt", "Equipments"))
        self.Equipment.setExpanded(True)

        ins = []
        outs = []
        for stream in items["in"]:
            for stream in items["in"][stream].down:
                ins.append(stream.id)
        for stream in items["out"]:
            for stream in items["out"][stream].up:
                outs.append(stream.id)

        for key in sorted(items["stream"].keys()):
            id = items["stream"][key].id
            if id in ins:
                item = QtWidgets.QTreeWidgetItem(self.Stream, 1)
                item.setText(0, str(id))
                item.setIcon(0, QtGui.QIcon(QtGui.QPixmap(
                    os.environ["pychemqt"] +
                    os.path.join("images", "equipment", "in.svg"))))
            elif id in outs:
                item = QtWidgets.QTreeWidgetItem(self.Stream, 2)
                item.setText(0, str(id))
                item.setIcon(0, QtGui.QIcon(QtGui.QPixmap(
                    os.environ["pychemqt"] +
                    os.path.join("images", "equipment", "out.svg"))))
            else:
                item = QtWidgets.QTreeWidgetItem(self.Stream, 3)
                item.setText(0, str(id))
                item.setIcon(0, QtGui.QIcon(QtGui.QPixmap(
                    os.environ["pychemqt"] +
                    os.path.join("images", "equipment", "stream.png"))))

        for equipment in items["equip"]:
            item = QtWidgets.QTreeWidgetItem(self.Equipment, 4)
            item.setText(0, "%i - %s" % (
                items["equip"][equipment].id, items["equip"][equipment].name))
            item.setIcon(0, QtGui.QIcon(QtGui.QPixmap(
                items["equip"][equipment].imagen)))


class PathConfig(QtWidgets.QWidget):
    """Custom widget for a file path show and configure functionality"""
    valueChanged = QtCore.pyqtSignal('QString')

    def __init__(self, title="", path="", patron="", msg="", folder=False,
                 save=False, parent=None):
        """
        title: Optional text an right of widget
        path: Inicial value for file path
        patron: File format to filter in file search dialog
        msg: Title of dialog file
        """
        super(PathConfig, self).__init__(parent)

        self.folder = folder
        self.save = save

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        if title:
            layout.addWidget(QtWidgets.QLabel(title))
            layout.addItem(QtWidgets.QSpacerItem(
                10, 10, QtWidgets.QSizePolicy.Fixed,
                QtWidgets.QSizePolicy.Fixed))

        self.path = QtWidgets.QLineEdit()
        self.path.setFixedHeight(24)
        self.path.textEdited.connect(self.pathEdited)
        layout.addWidget(self.path)
        self.boton = QtWidgets.QPushButton(
            QtWidgets.QApplication.translate("pychemqt", "Browse"))
        self.boton.setFixedHeight(24)
        self.boton.clicked.connect(self.select)
        layout.addWidget(self.boton)

        # Define default values for parameters don't defined
        if not patron:
            patron = QtWidgets.QApplication.translate(
                "pychemqt", "All files") + "(*)"
        elif patron == "exe":
            if sys.platform == "win32":
                patron = QtWidgets.QApplication.translate(
                    "pychemqt", "Executable files") + "(*.exe *.bat)"
            else:
                patron = QtWidgets.QApplication.translate(
                    "pychemqt", "All files") + "(*)"
        self.patron = patron

        if not msg:
            msg = QtWidgets.QApplication.translate(
                "pychemqt", "Select path of file")
        self.msg = msg
        self.setText(path)

    def text(self):
        return self.path.text()

    def setText(self, text):
        self.path.setText(text)

    def select(self):
        """Open the QFileDialog to select the file path"""
        dir = os.path.dirname(str(self.path.text()))
        if self.save:
            ruta = QtWidgets.QFileDialog.getSaveFileName(
                self, self.msg, dir, self.patron)[0]
        elif self.folder:
            ruta = QtWidgets.QFileDialog.getExistingDirectory(
                self, self.msg, dir)
        else:
            ruta = QtWidgets.QFileDialog.getOpenFileName(
                self, self.msg, dir, self.patron)[0]
        if ruta:
            self.path.setText(ruta)
            self.valueChanged.emit(ruta)

    def pathEdited(self, path):
        if os.path.isfile(path):
            self.valueChanged.emit(path)


class LineConfig(QtWidgets.QGroupBox):
    """Custom QGroupbox with all matplotlib Line configuration"""

    def __init__(self, confSection, title, parent=None):
        """
        confSection: Name key to identify the line
        title: Title to use in QGroupbox
        """
        super(LineConfig, self).__init__(title, parent)
        self.conf = confSection

        layout = QtWidgets.QHBoxLayout(self)
        self.Grosor = QtWidgets.QDoubleSpinBox()
        self.Grosor.setFixedWidth(60)
        self.Grosor.setAlignment(QtCore.Qt.AlignRight)
        self.Grosor.setRange(0.1, 5)
        self.Grosor.setDecimals(1)
        self.Grosor.setSingleStep(0.1)
        layout.addWidget(self.Grosor)
        self.Linea = LineStyleCombo()
        layout.addWidget(self.Linea)
        self.Marca = MarkerCombo()
        layout.addWidget(self.Marca)
        self.ColorButton = ColorSelector()
        layout.addWidget(self.ColorButton)
        layout.addItem(QtWidgets.QSpacerItem(
            10, 10, QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Fixed))

        # TODO: Add support for other properties of line:
        #     alpha
        #     markersize, markerfacecolor, markeredgewidth, markeredgecolor

    def setConfig(self, config, section="MEOS"):
        self.ColorButton.setColor(config.get(section, self.conf+'Color'))
        self.Grosor.setValue(config.getfloat(section, self.conf+'lineWidth'))
        self.Linea.setCurrentValue(config.get(section, self.conf+'lineStyle'))
        self.Marca.setCurrentValue(config.get(section, self.conf+'marker'))

    def value(self, config, section="MEOS"):
        config.set(section, self.conf+"Color", self.ColorButton.color.name())
        config.set(section, self.conf+"lineWidth", str(self.Grosor.value()))
        config.set(section, self.conf+"lineStyle", self.Linea.currentValue())
        config.set(section, self.conf+"marker", self.Marca.currentValue())
        return config

    @classmethod
    def default(cls, config, confSection, section="MEOS"):
        config.set(section, confSection+"Color", "#000000")
        config.set(section, confSection+"lineWidth", "0.5")
        config.set(section, confSection+"lineStyle", "-")
        config.set(section, confSection+"marker", "None")
        return config


class CustomCombo(QtWidgets.QComboBox):
    """General custom QComboBox"""
    valueChanged = QtCore.pyqtSignal("QString")

    def __init__(self, parent=None):
        super(CustomCombo, self).__init__(parent)
        self.setIconSize(QtCore.QSize(35, 18))
        self.currentIndexChanged.connect(self.emit)
        self._populate()

    def setCurrentValue(self, value):
        ind = self.key.index(value)
        self.setCurrentIndex(ind)

    def currentValue(self):
        return self.key[self.currentIndex()]

    def emit(self, ind):
        self.valueChanged.emit(self.key[ind])


class LineStyleCombo(CustomCombo):
    """Custom QComboBox for select matplotlib line styles"""
    key = ["None", "-", "--", ":", "-."]
    image = {
        "None":  "",
        "-": os.path.join("images", "button", "solid_line.png"),
        "--": os.path.join("images", "button", "dash_line.png"),
        ":": os.path.join("images", "button", "dot_line.png"),
        "-.": os.path.join("images", "button", "dash_dot_line.png")}

    def _populate(self):
        for key in self.key:
            self.addItem(QtGui.QIcon(QtGui.QPixmap(
                os.environ["pychemqt"] + self.image[key])), "")


class MarkerCombo(CustomCombo):
    """Custom QComboBox for select matplotlib line marker"""
    key = ["None", ".", ",", "o", "v", "^", "<", ">", "1", "2", "3", "4", "8",
           "s", "p", "*", "h", "H", "+", "x", "D", "d", "|", "_"]
    text = {"None": "", ".": "point", ",": "pixel", "o": "circle",
            "v": "triangle_down", "^": "triangle_up", "<": "triangle_left",
            ">": "triangle_right", "1": "tri_down", "2": "tri_up",
            "3": "tri_left", "4": "tri_right", "8": "octagon", "s": "square",
            "p": "pentagon", "*": "star", "h": "hexagon1", "H": "hexagon2",
            "+": "plus", "x": "x", "D": "diamond", "d": "thin_diamond",
            "|": "vline", "_": "hline"}

    def _populate(self):
        for key in self.key:
            txt = self.text[key]
            if txt:
                image = os.environ["pychemqt"] + \
                    os.path.join("images", "marker", "%s.png" % txt)
                self.addItem(QtGui.QIcon(QtGui.QPixmap(image)), self.text[key])
            else:
                self.addItem(self.text[key])


class InputFond(QtWidgets.QWidget):

    textChanged = QtCore.pyqtSignal("QString")
    fontChanged = QtCore.pyqtSignal("QFont")
    colorChanged = QtCore.pyqtSignal("QString")

    def __init__(self, text=None, font=None, parent=None):
        super(InputFond, self).__init__(parent)

        layout= QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.lineEdit=QtWidgets.QLineEdit()
        self.lineEdit.setSizePolicy(QtWidgets.QSizePolicy.Minimum,QtWidgets.QSizePolicy.Preferred)
        layout.addWidget(self.lineEdit)
        self.fontButton = QtWidgets.QPushButton(QtGui.QIcon(QtGui.QPixmap(os.environ["pychemqt"]+"/images/button/font.png")), "")
        self.fontButton.setFixedSize(24, 24)
        self.fontButton.setIconSize(QtCore.QSize(24, 24))
        self.fontButton.clicked.connect(self.fontButtonClicked)
        layout.addWidget(self.fontButton)
        self.colorButton = QtWidgets.QToolButton()
        self.colorButton.setFixedSize(24, 24)
        self.colorButton.clicked.connect(self.colorButtonClicked)
        layout.addWidget(self.colorButton)

        self.lineEdit.textChanged.connect(self.textChanged.emit)

    def setText(self, txt):
        self.lineEdit.setText(txt)

    def setColor(self, color):
        self.colorButton.setPalette(QtGui.QPalette(color))
        paleta = QtGui.QPalette()
        paleta.setColor(QtGui.QPalette.Text, color)
        self.lineEdit.setPalette(paleta)
        self.colorChanged.emit(color.name())

    def colorButtonClicked(self):
        """Dialogo de selección de color"""
        dialog=QtWidgets.QColorDialog(self.colorButton.palette().color(QtGui.QPalette.Button), self)
        if dialog.exec_():
            self.setColor(dialog.currentColor())

    def fontButtonClicked(self):
        """Dialogo de selección de color"""
        dialog=QtWidgets.QFontDialog(self.lineEdit.font())
        if dialog.exec_():
            self.lineEdit.setFont(dialog.currentFont())
            self.fontChanged.emit(dialog.currentFont())




class Table_Graphics(QtWidgets.QWidget):
    """Clase que define la tabla mostrada como popups al pasar el raton por encima de una entity"""
    def __init__(self, entity, id, preferences, parent=None):
        super(Table_Graphics, self).__init__(parent)
        self.setWindowFlags(QtCore.Qt.Popup)
        layout=QtWidgets.QVBoxLayout(self)
        if isinstance(entity, Corriente):
            title="Stream %i" %id
        else:
            title="Equipment %i" %id
        label=QtWidgets.QLabel(title)
        label.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(label)
        line = QtWidgets.QFrame()
        line.setFrameShape(QtWidgets.QFrame.HLine)
        line.setFrameShadow(QtWidgets.QFrame.Sunken)
        layout.addWidget(line)
        if entity:
            if entity.status:
                textos=entity.popup(preferences)
                for txt, tooltip, j in textos:
                        label=QtWidgets.QLabel(txt)
                        label.setToolTip(tooltip)
                        if j:
                            label.setAlignment(QtCore.Qt.AlignRight)
                        layout.addWidget(label)
            else:
                layout.addWidget(QtWidgets.QLabel(entity.msg))
        else:
            layout.addWidget(QtWidgets.QLabel(QtWidgets.QApplication.translate("pychemqt", "Undefined")))


class FlowLayout(QtWidgets.QLayout):
    def __init__(self, margin=0, spacing=0, parent=None):
        super(FlowLayout, self).__init__(parent)

        if parent is not None:
            self.setMargin(margin)

        self.setSpacing(spacing)

        self.itemList = []

    def __del__(self):
        item = self.takeAt(0)
        while item:
            item = self.takeAt(0)

    def addItem(self, item):
        self.itemList.append(item)

    def count(self):
        return len(self.itemList)

    def itemAt(self, index):
        if index >= 0 and index < len(self.itemList):
            return self.itemList[index]

        return None

    def takeAt(self, index):
        if index >= 0 and index < len(self.itemList):
            return self.itemList.pop(index)

        return None

    def expandingDirections(self):
        return QtCore.Qt.Orientations(QtCore.Qt.Orientation(0))

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        height = self.doLayout(QtCore.QRect(0, 0, width, 0), True)
        return height

    def setGeometry(self, rect):
        super(FlowLayout, self).setGeometry(rect)
        self.doLayout(rect, False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QtCore.QSize()

        for item in self.itemList:
            size = size.expandedTo(item.minimumSize())

        size = QtCore.QSize(
            size.width()+self.contentsMargins().left()+self.contentsMargins().right(),
            size.height()+self.contentsMargins().bottom()+self.contentsMargins().top())
        return size

    def doLayout(self, rect, testOnly):
        x = rect.x()
        y = rect.y()
        lineHeight = 0

        for item in self.itemList:
            wid = item.widget()
            spaceX = self.spacing() + wid.style().layoutSpacing(QtWidgets.QSizePolicy.PushButton, QtWidgets.QSizePolicy.PushButton, QtCore.Qt.Horizontal)*self.spacing()
            spaceY = self.spacing() + wid.style().layoutSpacing(QtWidgets.QSizePolicy.PushButton, QtWidgets.QSizePolicy.PushButton, QtCore.Qt.Vertical)*self.spacing()
            nextX = x + item.sizeHint().width() + spaceX
            if nextX - spaceX > rect.right() and lineHeight > 0:
                x = rect.x()
                y = y + lineHeight + spaceY
                nextX = x + item.sizeHint().width() + spaceX
                lineHeight = 0

            if not testOnly:
                item.setGeometry(QtCore.QRect(QtCore.QPoint(x, y), item.sizeHint()))

            x = nextX
            lineHeight = max(lineHeight, item.sizeHint().height())

        return y + lineHeight - rect.y()


def createAction(text, slot=None, shortcut=None, icon=None, tip=None,
                 checkable=False, button=False, parent=None):
    if not tip:
        tip = text
    action = QtWidgets.QAction(text, parent)
    if icon:
        action.setIcon(QtGui.QIcon(config.IMAGE_PATH + icon))
    if shortcut:
        action.setShortcut(shortcut)
    action.setToolTip(tip)
    action.setStatusTip(tip)
    if slot:
        action.triggered.connect(slot)
    if checkable:
        action.setCheckable(True)

    if button:
        boton = DragButton(parent)

        boton.setIcon(QtGui.QIcon(QtGui.QPixmap(config.IMAGE_PATH + icon)))
        boton.setToolTip(tip)
        boton.setStatusTip(tip)
        if slot:
            boton.clicked.connect(slot)
        boton.setCheckable(checkable)
        boton.setIconSize(QtCore.QSize(36, 36))
        boton.setFixedSize(QtCore.QSize(36, 36))
        return action, boton
    else:
        return action


def okToContinue(parent, dirty, func, parameters):
    """Function to ask user if any unsaved change
        parent: widget to close
        dirty: boolean to show any unsaved change
        func: function to run if user want to save changes
        parameters: parameter of func"""
    if not dirty:
        return True
    dialog = QtWidgets.QMessageBox.question(
        parent,
        QtWidgets.QApplication.translate("pychemqt", "Unsaved changes"),
        QtWidgets.QApplication.translate("pychemqt", "Save unsaved changes?"),
        QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No |
        QtWidgets.QMessageBox.Cancel, QtWidgets.QMessageBox.Yes)
    if dialog == QtWidgets.QMessageBox.Cancel:
        return False
    elif dialog == QtWidgets.QMessageBox.No:
        return True
    elif dialog == QtWidgets.QMessageBox.Yes:
        func(*parameters)
        return True


if __name__ == "__main__":
    from lib import unidades

    app = QtWidgets.QApplication(sys.argv)

    ui = QtWidgets.QDialog()
    layout = QtWidgets.QVBoxLayout(ui)

    w = Entrada_con_unidades(unidades.Pressure)
    layout.addWidget(w)
    w2 = ColorSelector(isAlpha=True)
    layout.addWidget(w2)
    w3 = PathConfig()
    layout.addWidget(w3)
    w4 = LineConfig("saturation", "Line Style")
    layout.addWidget(w4)

    ui.show()
    sys.exit(app.exec_())
