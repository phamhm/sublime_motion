'''
 go to line mode where the labels are at the begining of line
 and it's something like the relative number mode in vim
 1. Add relative line mode.
 2. draw labels at the begining of lines in reverse orders.
'''
import sublime
import sublime_plugin

from .motion import LabelObject

from .motion import BufferUndoCommand
from .motion import AddLabelsCommand
from .motion import JumpToLabelCommand
from .motion import draw_labels
from .motion import label_generator_singledouble
from .motion import draw_labels_in_range


class SublimeMotionWindowHackCommand(sublime_plugin.WindowCommand):

    def run(self, *kargs, **kwargs):
        self.mode = 'anything'
        self.panel_name = 'regex'
        self.max_input_panel = None
        self.view = self.window.active_view()
        self.literal = False
        self.multiple_selection = False
        self.range_select_mode = False

        for setting in kwargs:
            if hasattr(self, setting):
                setattr(self, setting, kwargs[setting])

        self.quick_panel = False
        self.quick_panel_multiple = self.quick_panel_till = ('1: Yes', '2: No')
        self.quick_panel_literal = ('1: Literal', '2: Not Literal')
        self.quick_panel_items = (self.quick_panel_literal,
                                  self.quick_panel_multiple,
                                  self.quick_panel_till)

        self.quick_panel_options = []
        self.show_panel()

    def quick_panel_option_rec(self, input):
        self.quick_panel_options.append(input)

    def show_panel(self):
        self.window.show_input_panel('Enter regex', '',
                                     self.on_done,
                                     self.on_change,
                                     self.on_change)

    def on_done(self, input):
        self.view.run_command('sublime_motion',
                              {'mode': self.mode,
                               'regex': input,
                               'literal': self.literal,
                               'multiple_selection': self.multiple_selection,
                               'range_select_mode': self.range_select_mode})

    def on_change(self, input):
        pass

    def on_cancel(self):
        pass


class SublimeMotionCommand(sublime_plugin.TextCommand):

    def init_settings(self, edit, *kargs, **kwargs):
        self.literal = False
        self.undo = False
        self.matched_region = None
        self.labels = LabelObject()
        self.label_gen = label_generator_singledouble()
        self.edit = edit

        self.scopes = ('invalid', 'string')
        self.keys = ('focus', 'unfocus', 'background')
        self.unfocus_flag = sublime.DRAW_NO_FILL

        # panel variables
        self.panel_init_text = ''
        self.panel_name = 'Jump To'
        self.max_panel_len = 2

        # available mode:[anything,above,below,right,left,char,word]

        # label every word in the view
        self.mode = "anything"

        # setup regex to match all word
        self.regex = r'\b[^\W]'

        # highlight everything from current position to label
        self.select_till = False

        # the region that matche the input label
        self.matched_region = None

        # enable selecting multiple labels
        # each label is separated by a comma ','
        self.multiple_selection = False
        self.range_select_mode = False
        self.range_select_list = []

        # If true highlight the enter word for editing
        # if false, only move the cursor to the begining of that word
        self.select_word = False

        # obtaining the current syntax of the view
        # syntax highlighting will be disabled while in sublime motion
        self.current_syntax = self.view.settings().get('syntax')

        # readding the setting file and reset the variables
        for setting in kwargs:
            if hasattr(self, setting):
                setattr(self, setting, kwargs[setting])

        # if we're in the 'word' mode, the panel lengh is not restricted.
        if self.mode == 'word':
            self.max_panel_len = 0

    def run(self, edit, *kargs, **kwargs):

        self.init_settings(edit, *kargs, **kwargs)

        self.labels_adder()

        # drawing labels before the selection panel is called
        draw_labels(self.view, self.keys,
                    self.scopes, self.labels,
                    self.unfocus_flag)

        #calling panel for user input
        self.view.window().show_input_panel(
            self.panel_name + ' ' + self.mode.capitalize(),
            self.panel_init_text,
            self.on_panel_done,
            self.on_panel_change,
            self.on_panel_cancel)

    def on_panel_done(self, input):
        if self.range_select_mode:
            self.undo_buffer() # remove all the labels in the view

            # find all matching regions
            focus_regions = []
            for label in self.range_select_list:
                region = self.labels.get_region_by_label(label)
                if region:
                    if self.select_word:
                        region = self.view.word(region)
                    focus_regions.append(region)

            # from the list of matching regions, select all labels
            if focus_regions:
                JumpToLabelCommand(self.view, self.edit, self.keys,
                                   focus_regions, True)
        else:
            # only jump to one label
            self.matched_region = self.labels.get_region_by_label(input)

            if self.matched_region:
                # if region is matched, remove the labels and jump to region
                self.undobuffer_and_jump()
            else:
                # if there is no matched, remove the labels
                self.undo_buffer()

    def on_panel_change(self, input):
        if not self.range_select_mode and self.max_panel_len and \
           len(input) > self.max_panel_len:
            self.terminate_panel()

        if self.range_select_mode:
            '''
            a,b,c,d0-d9,da-dz
            use rpartition, while comma is not entered yet, it's the field we're drawing/parsing
            '''

            self.range_select_list = input.rpartition(',')[0].split(',')

            focus_list = draw_labels_in_range(self.view, self.keys,
                                              self.scopes, self.labels,
                                              self.unfocus_flag,
                                              self.range_select_list)

        else:
            multiple_focuses, self.matched_region = \
                draw_labels(self.view, self.keys, self.scopes,
                            self.labels, self.unfocus_flag, input)

            if self.matched_region and len(multiple_focuses) == 1:
                self.terminate_panel()
                self.undobuffer_and_jump()

    def on_panel_cancel(self):
        '''
            Hit ESC to cancel the input panel
        '''
        self.undo_buffer()

    def undobuffer_and_jump(self):
        self.undo_buffer()
        self.jump()

    def undo_buffer(self):
        if not self.undo:
            self.undo = BufferUndoCommand(self.view, self.edit,
                                          self.keys, self.labels.is_empty())

    def jump(self):
        if self.matched_region:
            if self.select_word:
                self.matched_region = self.view.word(self.matched_region)
            JumpToLabelCommand(self.view, self.edit, self.keys,
                               # [self.matched_region.begin()],
                               [self.matched_region.begin()],
                               self.multiple_selection, self.select_till)

    def terminate_panel(self):
        self.view.window().run_command("hide_panel", {"cancel": True})

    def labels_adder(self):
        self.labels.clear()

        cursor = self.view.sel()[0].begin()

        visible_begin = self.view.visible_region().begin()
        visible_end = self.view.visible_region().end()

        beg = end = None

        if self.mode == 'above':
            end = cursor
            viewing_region = sublime.Region(visible_begin, cursor)
        elif self.mode == 'below':
            beg = cursor
            viewing_region = sublime.Region(cursor, visible_end)
        elif self.mode == 'left':
            beg = self.view.line(cursor).begin()
            end = cursor
            viewing_region = sublime.Region(beg, end)
        elif self.mode == 'right':
            beg = cursor
            end = self.view.line(cursor).end()
            viewing_region = sublime.Region(beg, end)
        else:
            viewing_region = sublime.Region(visible_begin, visible_end)

        self.view.add_regions(self.keys[2], [viewing_region], '')

        AddLabelsCommand(self.view, self.edit, self.regex,
                         self.labels, self.label_gen,
                         beg, end, self.literal)

    def labels_remover(self):
        self.labels.clear()
