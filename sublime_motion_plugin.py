'''
TODO:
1. visual mode selection from current pointer to mark
2. redraw in case multiple LABELS start with the same letter.
3. Currently, in multiple cursor mode, we can only choose one mark at a time.
    I'd like to refresh the panel to select multiple marks. Like choose a range
    of marks like [1-3] or provide a list of marks to select. May have issue
    with single and double char marks.
'''

import sublime
import sublime_plugin
from itertools import product
from itertools import permutations
from itertools import chain
from string import digits
from string import ascii_letters

class LabelObject(object):

    def __init__(self):
        self.viewid_regions = dict()  # key (viewid,label)
        self.label_regions = dict()
        self.viewid_label_regions = dict()
        self.all_views = dict()
        self.multiple_marks = []
        self.empty = True

    def add(self, view, label, region):
        viewid = view.id()

        if self.empty is True:
            self.empty = False

        if viewid not in self.viewid_regions:
            self.viewid_regions[viewid] = {label: region}
        else:
            self.viewid_regions[viewid][label] = region

        if label not in self.label_regions:
            label_len = len(label)
            if label_len > 1:
                partial_label = label[0:label_len-1]
            else:
                partial_label=None

                """what do i need to redraw?

                 view, labels, region
                """
            if partial_label is not None and partial_label in self.label_regions:
                self.multiple_marks.append((label, view, region))

            self.label_regions[label] = (view, region)

        if viewid not in self.all_views:
            self.all_views[viewid] = view

        self.viewid_label_regions[(viewid, label,)] = region

    def find_region_by_label(self, label):
        if label in self.label_regions:
            return self.label_regions[label]
        return None

    def get_region_by_label(self):
        return self.label_regions

    def get_regions_by_viewid(self, viewid):
        if viewid in self.viewid_regions:
            return self.viewid_regions[viewid]
        return None

    def get_all_views(self):
        return self.all_views

    def is_empty(self):
        return self.empty

    def partial_labels_remap(self, key):
        tmp_labels = LabelObject()

        for label in self.label_regions:
            if key != '' and key != label and key == label[0:len(key)]:
                view, region = self.label_regions[label]
                tmp_labels.add(view, label, region)

        return tmp_labels

    def empty_everything(self):
        if self.empty is False:
            # self.viewid_regions.clear()
            self.label_regions.clear()
            self.viewid_label_regions.clear()
            self.all_views.clear()
        self.empty = True

LABELS = None
LABEL_GEN = None

def label_generator_singledouble():
    product =  (tup[0] + tup[1] for tup in permutations(digits+ascii_letters, 2))
    return chain(ascii_letters,digits,product)

def label_generator_double():
    return  (tup[0] + tup[1] for tup in permutations(ascii_letters+digits, 2))


class SublimeMotionCommand(sublime_plugin.WindowCommand):

    def init_settings(self,*kargs,**kwargs):
        global LABEL_GEN

        self.key = 'sublime_motion'

        self.panel_init_text = ''
        self.panel_name = 'Jump To'
        self.max_panel_len = 2

        # available mode:[all,above,below,right,left,char,word]
        self.mode="all"
        self.regex = r'\b[^\W]'
        self.multiple_selection = False

        #setting the variables from the key-map
        for setting in kwargs:
            if hasattr(self,setting):
                setattr(self,setting,kwargs[setting])

        # if self.mode == "all":
        #     LABEL_GEN = label_generator_double()
        # elif self.mode == "relative_line":
        #     LABEL_GEN = label_generator_relative_num()
        # else:
        LABEL_GEN = label_generator_singledouble()


    def run(self,*kargs,**kwargs):
        self.init_settings(*kargs,**kwargs)

        if self.mode in ['char','word']:
            self.label_add_special()
        else:
            self.labels_adder()
            self.show_panel(self.panel_name,
                         self.panel_init_text,
                         self.on_panel_done,
                         self.on_panel_change,
                         self.on_panel_cancel)

    def show_panel(self,name, init_text, done=None, change=None, cancel=None):
        self.window.show_input_panel(name, init_text,
                                     done, change, cancel)
    def on_panel_done(self, input):
        global LABELS

        if not LABELS.is_empty():
            res = LABELS.find_region_by_label(input)
            if res is not None:
                view, region = res

                self.labels_remover(self.key)

                self.window.focus_view(view)
                view.run_command('jump_to_label', {"target": region.begin(),
                        "multiple_selection":self.multiple_selection})
            else:
                self.labels_remover(self.key)

    def on_panel_change(self, input):
        global LABELS

        if len(input) == 0 and not LABELS.is_empty():
            for view in LABELS.get_all_views().values():
                view.run_command('draw_labels', {'key': self.key})
        elif len(input)>self.max_panel_len:
            self.terminate_panel()

        if not LABELS.is_empty() and len(input)>0:
            res = LABELS.find_region_by_label(input)

            # print('debug res',res)
            # if res is not None and res[0] is True:
            #     tmp_label_region = LABELS.get_region_by_label()
            #     print('debug ',len(tmp_label_region),input)
            #     for view in LABELS.get_all_views().values():
            #         view.run_command('remove_labels', {'key': self.key})
            #     # for (multiple_flag,view,region) in LABELS.get_region_by_label().values():
            #     #     print('debug label',input,region)
            #     #     if multiple_flag is True:
            #     #         view.run_command('draw_labels', {'key': self.key})
            #     return


            if res is not None:
                view, region = res
                self.labels_remover(self.key)

                self.window.focus_view(view)
                view.run_command('jump_to_label', {"target": region.begin(),
                        "multiple_selection":self.multiple_selection})

                self.window.run_command("hide_panel", {"cancel": True})
            elif len(input)>3:
                self.terminate_panel()
        elif len(input)>0:
            self.terminate_panel()


    def terminate_panel(self):
        self.labels_remover(self.key)
        self.window.run_command("hide_panel", {"cancel": True})


    def on_panel_cancel(self):
        self.labels_remover(self.key)


    def labels_adder(self):
        global LABELS

        self.labels_remover(self.key)

        LABELS = LabelObject()
        if self.mode == "all":
            self.label_add_all()
        elif self.mode in ["above","below","left","right"]:
            self.label_add_partial()

    def label_add_all(self):
        for group in range(self.window.num_groups()):
            view = self.window.active_view_in_group(group)
            if self.mode=='char':
                view.run_command(
                    'add_labels', {'regex': self.regex,'literal':True})
            else:
                view.run_command(
                    'add_labels', {'regex': self.regex})
            # view.run_command('draw_labels', {'key': self.key})


    def label_add_partial(self):
        global LABELS

        self.labels_remover(self.key)

        LABELS = LabelObject()

        view = self.window.active_view()

        cursor = view.sel()[0].begin()
        beg = None
        end = None
        if self.mode == 'above':
            beg = None
            end = cursor
        elif self.mode == 'below':
            beg = cursor
            end = None
        elif self.mode == 'left':
            beg = view.line(cursor).begin()
            end = cursor
        elif self.mode == 'right':
            beg = cursor
            end = view.line(cursor).end()

        view.run_command(
            'add_labels', {'regex': self.regex, 'beg': beg, 'end': end})
        # view.run_command('draw_labels', {'key': self.key})

    def label_add_special(self):

        global LABELS

        self.labels_remover(self.key)

        LABELS = LabelObject()

        self.show_panel("Enter "+self.mode.capitalize(),'',self.on_special_panel_done,
                    self.on_special_panel_change,
                    self.on_special_panel_cancel)

    def on_special_panel_done(self,input):
        if self.mode=='word':
            self.regex=input
            self.label_add_all()
            self.window.run_command("hide_panel", {"cancel": True})

            self.show_panel(self.panel_name,
                         self.panel_init_text,
                         self.on_panel_done,
                         self.on_panel_change,
                         self.on_panel_cancel)

    def on_special_panel_change(self,input):
        if self.mode=='char' and len(input)==1:
            self.regex=input

            self.label_add_all()
            self.window.run_command("hide_panel", {"cancel": True})

            self.show_panel(self.panel_name,
                         self.panel_init_text,
                         self.on_panel_done,
                         self.on_panel_change,
                         self.on_panel_cancel)

    def on_special_panel_cancel(self):
        pass


    def Add_manager(self, view, beg=None, end=None):
        '''
        DO NOT CALL
        when used, this function may cause multiple 'undo' events
        '''
        global LABELS

        if beg is None:
            beg = view.visible_region().begin()

        if end is None:
            end = view.visible_region().end()

        work_region = sublime.Region(beg, end)

        tmp_label = []
        for region in view.find_all(self.regex):
            if not region.empty() and work_region.contains(region):
                tmp_label.append((view,region))
        return tmp_label


    def labels_remover(self, key):
        global LABELS

        if isinstance(LABELS, LabelObject):
            if not LABELS.is_empty():
                for view in LABELS.get_all_views().values():
                    view.run_command('remove_labels', {'key': key})
                LABELS.empty_everything()


class AddLabelsCommand(sublime_plugin.TextCommand):
    '''
    '''

    def run(self, edit, regex, beg=None, end=None, literal = False):
        global LABELS, LABEL_GEN

        if beg is None:
            beg = self.view.visible_region().begin()

        if end is None:
            end = self.view.visible_region().end()

        work_region = sublime.Region(beg, end)

        # find_all returns a huge amount of regions that is not in the visible region
        # if literal is True:
        #     matched_regions = self.view.find_all(regex,sublime.LITERAL)
        # else:
        #     matched_regions = self.view.find_all(regex)
        # for region in matched_regions:
        #     if not region.empty() and work_region.contains(region):
        #         key = next(LABEL_GEN)
        #         region = sublime.Region(
        #             region.begin(), region.begin() + len(key))
        #         LABELS.add(self.view, key, region)

        while(beg is not None and beg < end):
            if literal is True:
                region = self.view.find(regex,beg,sublime.LITERAL)
            else:
                region = self.view.find(regex,beg)

            if region is not None and not region.empty() and work_region.contains(region):
                beg = region.end()

                key = next(LABEL_GEN)
                region = sublime.Region(
                    region.begin(), region.begin() + len(key))
                LABELS.add(self.view, key, region)
            else:
                beg = None


class DrawLabelsCommand(sublime_plugin.TextCommand):

    def run(self, edit, key):
        global LABELS

        viewid = self.view.id()
        region_map = LABELS.get_regions_by_viewid(viewid)
        self.regions = []
        if region_map is not None:
            for label in region_map:
                region = region_map[label]
                self.regions.append(region)
                self.view.replace(edit, region, label)

            self.view.add_regions(key, self.regions, 'invalid')
# need a draw partial label


class RemoveLabelsCommand(sublime_plugin.TextCommand):

    """Command for removing LABELS from views"""

    def run(self, edit, key):
        self.view.erase_regions(key)
        self.view.end_edit(edit)
        self.view.run_command("undo")

class JumpToLabelCommand(sublime_plugin.TextCommand):
    """Command to jump to the selected label from the views"""

    def run(self, edit, target, multiple_selection = False):
        if not multiple_selection:
            self.view.sel().clear()
        region = sublime.Region(target)
        self.view.sel().add(region)
        self.view.show(target)
