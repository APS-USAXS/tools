'''
table of Q values and computed  motor positions
'''


from PyQt4 import QtCore, QtGui
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

    def rowCount(self, parent):
        return len(self.model)

    def columnCount(self, parent):
        return len(self.model[0])

    def headerData(self, col, orientation, role):
        if orientation == QtCore.Qt.Horizontal:
            if role == QtCore.Qt.DisplayRole:
                return QtCore.QVariant(self.headers[col])
        return QtCore.QVariant()

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
                    if self.recalc is not None:
                        result = self.recalc(val)
                        if result is not None:
                            ar, ay, dy = result
                            self.model[row][AR_COLUMN] = ar
                            self.model[row][AY_COLUMN] = ay
                            self.model[row][DY_COLUMN] = dy
                    return True
        return False

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


class TableView(QtGui.QTableView):
    """
    A table to demonstrate the button delegate.
    """
    def __init__(self, doMove=None, *args, **kwargs):
        super(TableView, self).__init__(*args, **kwargs)
        
        self.setAlternatingRowColors(True)
 
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
