Aug 14, 2015:
The program was suffering from undoing mishaps. When the labels are not being drawn, the undo command undid previous modification to the model before the sublime-motion was called. In order to solve this issue, the UndoBufferCommand will only call the command('undo') when labels object is not empty

Also, then entering a label that doesn't belong to self.labels, the undo command was not called. Why?
