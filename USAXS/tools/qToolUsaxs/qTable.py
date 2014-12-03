'''
table of Q values and computed  motor positions
'''


from PyQt4 import QtCore, QtGui
from bcdaqwidgets import BcdaQLabel, StyleSheet
pyqtSignal = QtCore.pyqtSignal
import datetime


LABEL_COLUMN    = 0
Q_COLUMN        = 1
AR_COLUMN       = 2
AY_COLUMN       = 3
DY_COLUMN       = 4
DEFAULT_NUMBER_ROWS = 30


# TODO: table width (and column widths) should change when window size changes
# custom TableView widget should fit into the window
# this means no horizontal scroll bar


class TableModel(QtCore.QAbstractTableModel):
    """
    Model (data) of our table of motor positions for each Q
    
    :datain [[label,Q]]: the data model, list of list(label,Q) values, if None, a default model is created
    :parent obj: groupBox that contains this model and related view
    :recalc obj: method that computes AR, AY, & DY from Q and user parameters
    """
    
    def __init__(self, datain, parent=None, recalc=None, *args):
        super(TableModel, self).__init__(parent, *args)
        self.view = None
        self.motors = None
        self.model = []
        self.recalc = recalc
        self.headers = ['description', 'Q, 1/A', 'AR, degrees', 'AY, mm', 'DY, mm',]
        if datain is None:
            for _ in range(DEFAULT_NUMBER_ROWS):
                self.newRow()
        else:
            for row in datain:
                self.newRow(row)
    
    def newRow(self, data = None):
        if data is None:
            now = str(datetime.datetime.now())
            self.model.append([now, 0, 0, 0, 0, ])
        else:
            if not isinstance(data, list):
                raise RuntimeError('each row must contain values for: label, Q')
            self.model.append(data + [0, 0, 0])
        self.calc_row(len(self.model)-1)

    def rowCount(self, parent):
        return len(self.model)

    def columnCount(self, parent):
        return len(self.model[0])

    def headerData(self, col, orientation, role):
        if orientation == QtCore.Qt.Horizontal:
            if role == QtCore.Qt.DisplayRole:
                return QtCore.QVariant(self.headers[col])
        return QtCore.QVariant()

    def flags(self, index):
        defaultFlags = QtCore.QAbstractItemModel.flags(self, index)
        if index.isValid():
            return defaultFlags \
                    | QtCore.Qt.ItemIsEnabled \
                    | QtCore.Qt.ItemIsEditable \
                    | QtCore.Qt.ItemIsDragEnabled \
                    | QtCore.Qt.ItemIsDropEnabled
           
        else:
            return defaultFlags \
                    | QtCore.Qt.ItemIsEnabled \
                    | QtCore.Qt.ItemIsDropEnabled

    def data(self, index, role):
        if index.isValid():
            if role in (QtCore.Qt.DisplayRole, QtCore.Qt.EditRole):
                return QtCore.QVariant(self.model[index.row()][index.column()])
        return QtCore.QVariant()

    def setData(self, index, value, role=QtCore.Qt.DisplayRole):
        '''update the model from the control'''
        if index.isValid():
            row = index.row()
            column = index.column()
            if column == LABEL_COLUMN:
                self.model[row][column] = str(value.toString())
                return True
            elif column == Q_COLUMN:
                val, ok = value.toDouble()
                if ok:
                    self.model[row][column] = val
                    self.calc_row(row)
                    return True
            elif column in (AR_COLUMN, AY_COLUMN, DY_COLUMN):
                    self.model[row][column] = value
                    return True
        return False
    
    def setView(self, view):
        self.view = view
    
    def setMotors(self, motors):
        self.motors = motors

    def calc_row(self, row):
        if self.recalc is not None:
            Q = self.model[row][Q_COLUMN]
            result = self.recalc(Q)
            if result is not None:
                ar, ay, dy = result
                index_ar = self.index(row, AR_COLUMN)
                index_ay = self.index(row, AY_COLUMN)
                index_dy = self.index(row, DY_COLUMN)

                self.setData(index_ar, ar, QtCore.Qt.EditRole)
                self.setData(index_ay, ay, QtCore.Qt.EditRole)
                self.setData(index_dy, dy, QtCore.Qt.EditRole)
        
                def set_background_color(mne, index, value):
                    # FIXME: some buttons (offscreen ones, for example) don't get colors yet
                    clut = {False: 'yellow', True: 'mintcream'}
                    color = clut[self.motors[mne].inLimits(value)]
                    sty = StyleSheet(self.view.indexWidget(index))
                    sty.updateStyleSheet({'background-color': color})
                
                set_background_color('ar', index_ar, ar)
                set_background_color('ay', index_ay, ay)
                set_background_color('dy', index_dy, dy)

                # trigger the GUI to redraw
                self.view.dataChanged(index_ar, index_dy)

    def calc_all(self):
        for row, model in enumerate(self.model):
            if len(model[Q_COLUMN]) > 0:
                self.calc_row(row)


class TableView(QtGui.QTableView):
    """
    A table to demonstrate the button delegate.
    """
    def __init__(self, doMove=None, *args, **kwargs):
        super(TableView, self).__init__(*args, **kwargs)
        
        self.setAlternatingRowColors(True)
        #self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
 
        self.doMove = doMove
        #self.q_control = FloatControl(self, self.AR_ButtonClicked, '%.6f')
        self.q_control = FloatControl()
        self.setItemDelegate(self.q_control)
        
        self.ar_control = ButtonControl(self, self.AR_ButtonClicked, '%.6f')
        self.ay_control = ButtonControl(self, self.AY_ButtonClicked, '%.3f')
        self.dy_control = ButtonControl(self, self.DY_ButtonClicked, '%.3f')

        self.setItemDelegateForColumn(AR_COLUMN, self.ar_control)
        self.setItemDelegateForColumn(AY_COLUMN, self.ay_control)
        self.setItemDelegateForColumn(DY_COLUMN, self.dy_control)

    def _buttonClicked(self, buttonname='', *args, **kw):
        gb = self.parent()
        w = gb.parent()
        mw = w.parent()
        statusbar = mw.statusBar()
        msg = buttonname + ' button: ' + self.sender().text()
        statusbar.showMessage(msg)
        if self.doMove is not None:
            self.doMove(buttonname, self.sender().text())

    def AR_ButtonClicked(self):
        self._buttonClicked('AR')
 
    def AY_ButtonClicked(self):
        self._buttonClicked('AY')
 
    def DY_ButtonClicked(self):
        self._buttonClicked('DY')


class FloatControl(QtGui.QStyledItemDelegate):
    '''Constrained floating-point input on Q column'''
    def createEditor(self, widget, option, index):
        if not index.isValid():
            return 0
        if index.column() == Q_COLUMN:     #only on the cells in the Q column
            editor = QtGui.QLineEdit(widget)
            validator = QtGui.QDoubleValidator()
            editor.setValidator(validator)
            return editor
        return super(FloatControl, self).createEditor(widget, option, index)


class ButtonControl(QtGui.QItemDelegate):
    '''A QPushButton in every cell of the column to which it's applied'''
    def __init__(self, parent, action, display_format='%f'):
        QtGui.QItemDelegate.__init__(self, parent)
        self.action = action
        self.format = display_format
 
    def paint(self, painter, option, index):
        widget = self.parent().indexWidget(index)
        if widget is None:
            # create the PushButton widget
            value, ok = index.data().toDouble()     # *MUST* be a double
            if ok:
                text = self.format % value
                owner = self.parent()
                pb = QtGui.QPushButton(text, owner, clicked=self.action)
                owner.setIndexWidget(index, pb)
        else:
            if isinstance(widget, QtGui.QPushButton):
                # update the PushButton text if the model's value changed
                value, ok = index.data().toDouble()
                if ok:
                    text = self.format % value
                    if text != widget.text():
                        widget.setText(text)    # update only if non-trivial
