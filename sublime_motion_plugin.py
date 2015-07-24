'''
TODO:
1. visual mode selection from current pointer to mark. DONE
2. redraw in case multiple LABELS start with the same letter. DONE
3. Currently, in multiple cursor mode, we can only choose one mark at a time.
    I'd like to refresh the panel to select multiple marks. Like choose a range
    of marks like [1-3] or provide a list of marks to select. May have issue
    with single and double char marks.
4. change tuple to namedtuple
5. two char label will overwrite the CRLF if the word at label is shorter than the label
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
            region_info = (label,view.id(),region,)
            if partial_label is not None and partial_label in self.label_regions:
                self.label_regions[partial_label].append(region_info)

            self.label_regions[label] = [region_info]

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

    def clear(self):
            # self.viewid_regions.clear()
        self.label_regions.clear()
        self.viewid_label_regions.clear()
        self.all_views.clear()
        self.empty = True

LABELS = LabelObject()
REDRAW_LABELS=dict()
LABEL_GEN = None

def label_generator_singledouble():
    # product =  (tup[0] + tup[1] for tup in permutations(digits+ascii_letters, 2))
    # return chain(ascii_letters,digits,product)
    return chain(ascii_letters,digits[::-1],product(digits+ascii_letters,repeat=2))

def label_generator_double():
    return  (tup[0] + tup[1] for tup in permutations(ascii_letters+digits, 2))


class SublimeMotionCommand(sublime_plugin.WindowCommand):

    def init_settings(self,*kargs,**kwargs):
        global LABEL_GEN
        global LABELS,REDRAW_LABELS

        LABELS.clear(), REDRAW_LABELS.clear()

        self.key = 'sublime_motion'
        self.buffer_mod = 'buffer_mod'

        self.panel_init_text = ''
        self.panel_name = 'Jump To'
        self.max_panel_len = 2

        # available mode:[anything,above,below,right,left,char,word]
        self.mode="anything"
        self.regex = r'\b[^\W]'
        self.multiple_selection = False
        self.select_till = False

        #setting the variables from the key-map
        for setting in kwargs:
            if hasattr(self,setting):
                setattr(self,setting,kwargs[setting])

        LABEL_GEN = label_generator_singledouble()


    def run(self,*kargs,**kwargs):
        self.init_settings(*kargs,**kwargs)

        if self.mode in ['char','word']:
            self.label_add_special()
        else:
            self.labels_adder()
            self.show_panel(self.panel_name+' '+self.mode.capitalize(),
                         self.panel_init_text,
                         self.on_panel_done,
                         self.on_panel_change,
                         self.on_panel_cancel)

    def show_panel(self,name, init_text, done=None, change=None, cancel=None):
        self.window.show_input_panel(name, init_text,
                                     done, change, cancel)

    def on_panel_done(self, input):
        global LABELS

        print('in panel done')

        if not LABELS.is_empty():
            res = LABELS.find_region_by_label(input)
            if res is not None:
                viewid, region = res[0][1:]

                view = LABELS.get_all_views()[viewid]
                self.labels_remover(self.key)
                # self.window.focus_view(view)
                view.run_command('jump_to_label', {"target": region.begin(),
                        "multiple_selection":self.multiple_selection,
                        "select_till":self.select_till})

        self.labels_remover(self.key)


    def on_panel_change(self, input):
        global LABELS, REDRAW_LABELS

        print('in panel change',input)

        if len(input) == 0 and not LABELS.is_empty():
            for view in LABELS.get_all_views().values():
                if REDRAW_LABELS:
                    view.run_command('buffer_undo', {'key': self.key})
                view.run_command('draw_labels', {'key': self.key})
        elif len(input)>self.max_panel_len:
            self.terminate_panel()

        if not LABELS.is_empty() and len(input)>0:
            res = LABELS.find_region_by_label(input)

            if res is not None and len(res)>1:
                for view in LABELS.get_all_views().values():
                    view.run_command('buffer_undo', {'key': self.key})

                REDRAW_LABELS.clear()
                for item in res:
                    viewid = item[1]
                    if item[0].startswith(input):
                        if viewid in REDRAW_LABELS:
                            REDRAW_LABELS[viewid].append(item)
                        else:
                            REDRAW_LABELS[viewid] = [item]

                for view in LABELS.get_all_views().values():
                    view.run_command('draw_partial_labels',{'key':self.key})
                return

            if res is not None:
                viewid, region = res[0][1:]

                view = LABELS.get_all_views()[viewid]

                self.labels_remover(self.key)
                # self.window.focus_view(view)
                view.run_command('jump_to_label', {"target": region.begin(),
                        "multiple_selection":self.multiple_selection,
                        "select_till":self.select_till})

                self.window.run_command("hide_panel", {"cancel": True})
            elif len(input)>3:
                self.terminate_panel()
        elif len(input)>0:
            self.terminate_panel()


    def terminate_panel(self):
        self.labels_remover(self.key)
        self.window.run_command("hide_panel", {"cancel": True})


    def on_panel_cancel(self):
        print('on cancel')
        self.labels_remover(self.key)


    def labels_adder(self):
        global LABELS

        self.labels_remover(self.key)

        if self.mode == "anything":
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
        global LABELS, REDRAW_LABELS

        if not LABELS.is_empty():
            for view in LABELS.get_all_views().values():
                view.run_command('buffer_undo', {'key': key})
        REDRAW_LABELS.clear()
        LABELS.clear()


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

        while(beg is not None and beg < end):
            if literal is True:
                region = self.view.find(regex,beg,sublime.LITERAL)
            else:
                region = self.view.find(regex,beg)

            if region is not None and not region.empty() and work_region.contains(region):
                beg = region.end()

                label = ''.join(next(LABEL_GEN))

                region = sublime.Region(
                    region.begin(), region.begin() + len(label))
                LABELS.add(self.view, label, region)
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

class DrawPartialLabelsCommand(sublime_plugin.TextCommand):

    def run(self, edit, key):
        global REDRAW_LABELS

        self.regions = []

        viewid = self.view.id()
        if viewid in REDRAW_LABELS:
            redraw_list = REDRAW_LABELS[viewid]
            for (label,ignore,region) in redraw_list: # ignore=viewid, this is hackish, need to remove
                self.view.replace(edit, region, label)
                self.regions.append(region)
            self.view.add_regions(key, self.regions, 'invalid')


class AddSpaceCommand(sublime_plugin.TextCommand):
    '''add space to the end of the letter'''
    def run(self, edit, key):
        pass

class BufferUndoCommand(sublime_plugin.TextCommand):
    """Command for removing LABELS from views"""

    def run(self, edit, key):
        self.view.erase_regions(key)
        self.view.end_edit(edit)
        self.view.run_command("undo")

class JumpToLabelCommand(sublime_plugin.TextCommand):
    """Command to jump to the selected label from the views"""

    def run(self, edit, target, multiple_selection = False, select_till = False):
        region = sublime.Region(target)

        if select_till is True:
            region_list =[self.view.sel()[0].begin(),
                        self.view.sel()[0].end(),
                        region.begin(),
                        region.end()]
            beg = min(region_list)
            end = max(region_list)
            self.view.sel().add(sublime.Region(beg,end))
        else:
            if not multiple_selection:
                self.view.sel().clear()
            self.view.sel().add(region)

        self.view.show(target)
