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
            self.label_regions[label] = (view, region,)

        if viewid not in self.all_views:
            self.all_views[viewid] = view

        self.viewid_label_regions[(viewid, label,)] = region

    def find_region_by_label(self, label):
        if label in self.label_regions:
            return self.label_regions[label]
        return None

    def get_regions_by_viewid(self, viewid):
        if viewid in self.viewid_regions:
            return self.viewid_regions[viewid]
        return None

    def find_region_by_viewid_label(self, viewid, label):
        try:
            res = self.viewid_regions[viewid][label]
        except KeyError:
            res = None
        return res

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
            del self.viewid_regions
            del self.label_regions
            del self.viewid_label_regions
            del self.all_views
        self.empty = True

labels = None

def label_generator_double():
    return (tup[0] + tup[1] for tup in permutations(ascii_letters+digits, 2))

def label_generator_single():
    return chain(ascii_letters, digits)

label_gen = label_generator_double()


class SublimeMotionCommand(sublime_plugin.WindowCommand):

    def init_settings(self):
        self.regex = self.set_regex()
        self.key = 'sublime_motion'
        self.panel_init_text = self.set_panel_init_text()
        self.panel_name = self.set_panel_name()
        self.max_panel_len = self.set_max_panel_len()

    def set_label_gen(self):
        return label_generator_double()

    def set_regex(self):
        return r'\b[^\W]'

    def set_panel_name(self):
        return 'Jump To'

    def set_panel_init_text(self):
        return ''

    def set_max_panel_len(self):
        return 2

    def run(self):
        global label_gen
        self.init_settings()
        label_gen = self.set_label_gen()
        self.labels_adder()
        self.window.show_input_panel(self.panel_name, self.panel_init_text,
                                     self.on_panel_done, self.on_panel_change,
                                     self.on_panel_cancel)

    def on_panel_done(self, input):
        global labels

        if not labels.is_empty():
            res = labels.find_region_by_label(input)
            if res is not None:
                view, region = res

                self.labels_remover(self.key)

                self.window.focus_view(view)
                view.run_command('jump_to_label', {"target": region.begin()})
            else:
                self.labels_remover(self.key)

    def on_panel_change(self, input):
        global labels

        # if not labels.is_empty():
        #     res = labels.find_region_by_label(input)
        #     partial = labels.partial_labels_remap(input)

        #     if res is not None and partial.is_empty():
        #         view, region = res

        #         self.labels_remover(self.key)

        #         self.window.focus_view(view)
        #         view.run_command('jump_to_label', {"target": region.begin()})

        #         self.window.run_command("hide_panel", {"cancel": True})
        #     elif res is None and not partial.is_empty():
        #         self.labels_remover(self.key)
        #         labels = partial

        #         for view in labels.get_all_views().values():
        #             view.run_command('draw_labels', {'key': self.key})
        # else:
        #     self.labels_remover(self.key)
        #     self.window.run_command("hide_panel", {"cancel": True})

        if len(input)>self.max_panel_len:
            self.terminate_panel()

        if not labels.is_empty():
            res = labels.find_region_by_label(input)

            # if res is None and len(input)==self.max_panel_len:
            #     self.terminate_panel()

            if res is not None:
                view, region = res
                self.labels_remover(self.key)

                self.window.focus_view(view)
                view.run_command('jump_to_label', {"target": region.begin()})

                self.window.run_command("hide_panel", {"cancel": True})
            elif len(input)>3:
                self.terminate_panel()
        else:
            self.terminate_panel()
    def terminate_panel(self):
        self.labels_remover(self.key)
        self.window.run_command("hide_panel", {"cancel": True})

    def on_panel_cancel(self):
        self.labels_remover(self.key)

    def labels_adder(self):
        global labels

        self.labels_remover(self.key)

        labels = LabelObject()
        for group in range(self.window.num_groups()):
            view = self.window.active_view_in_group(group)
            view.run_command(
                'add_labels', {'regex': self.regex})
            view.run_command('draw_labels', {'key': self.key})

    # def labels_adder(self):
    #     global labels

    #     self.labels_remover(self.key)

    #     labels = LabelObject()
    #     tmp_label=[]

    #     for group in range(self.window.num_groups()):
    #         view = self.window.active_view_in_group(group)
    #         # view.run_command('add_labels', {'regex': self.regex})
    #         # view.run_command('draw_labels', {'key': self.key})
    #         tmp_label.extend(self.Add_manager(view))

    #     if len(tmp_label)>(len(ascii_letters)+len(digits)):
    #         label_gen = label_generator_double()
    #     else:
    #         label_gen = label_generator_single()

    #     for (view,region) in tmp_label:
    #         key = next(label_gen)
    #         region = sublime.Region(
    #             region.begin(), region.begin() + len(key))
    #         labels.add(view, key, region)

    #     for view in labels.get_all_views().values():
    #         view.run_command('draw_labels', {'key': self.key})

    def Add_manager(self, view, beg=None, end=None):
        global labels

        if beg is None:
            beg = view.visible_region().begin()

        if end is None:
            end = view.visible_region().end()

        work_region = sublime.Region(beg, end)

        tmp_label = []
        for region in view.find_all(self.regex):
            if not region.empty() and work_region.contains(region):
                # region = sublime.Region(
                #     region.begin(), region.begin() + len(key))
                # labels.add(self.view, key, region)
                tmp_label.append((view,region))
        return tmp_label


    def labels_remover(self, key):
        global labels

        if isinstance(labels, LabelObject):
            if not labels.is_empty():
                for view in labels.get_all_views().values():
                    view.run_command('remove_labels', {'key': key})
                labels.empty_everything()


class AddLabelsCommand(sublime_plugin.TextCommand):

    ''' need an object for :
    '''

    def run(self, edit, regex, beg=None, end=None):
        global labels, label_gen

        if beg is None:
            beg = self.view.visible_region().begin()

        if end is None:
            end = self.view.visible_region().end()

        work_region = sublime.Region(beg, end)

        for region in self.view.find_all(regex):
            if not region.empty() and work_region.contains(region):
                key = next(label_gen)
                region = sublime.Region(
                    region.begin(), region.begin() + len(key))
                labels.add(self.view, key, region)


class DrawLabelsCommand(sublime_plugin.TextCommand):

    def run(self, edit, key):
        global labels

        viewid = self.view.id()
        region_map = labels.get_regions_by_viewid(viewid)
        self.regions = []
        if region_map is not None:
            for label in region_map:
                region = region_map[label]
                self.regions.append(region)
                self.view.replace(edit, region, label)

            self.view.add_regions(key, self.regions, 'invalid')


class RemoveLabelsCommand(sublime_plugin.TextCommand):

    """Command for removing labels from the views"""

    def run(self, edit, key):
        self.view.erase_regions(key)
        self.view.end_edit(edit)
        self.view.run_command("undo")

class JumpToLabelCommand(sublime_plugin.TextCommand):

    def run(self, edit, target):
        self.view.sel().clear()
        region = sublime.Region(target)
        self.view.sel().add(region)
        self.view.show(target)


class SublimeMotionBelowCommand(SublimeMotionCommand):
    def set_label_gen(self):
        return label_generator_single()

    def labels_adder(self):
        global labels

        self.labels_remover(self.key)

        labels = LabelObject()
        view=self.window.active_view()
        view.run_command(
            'add_labels',
            {'regex': self.regex, 'beg': view.sel()[0].begin()}
        )
        view.run_command('draw_labels', {'key': self.key})


class SublimeMotionAboveCommand(SublimeMotionCommand):
    def set_label_gen(self):
        return label_generator_single()

    def labels_adder(self):
        global labels

        self.labels_remover(self.key)

        labels = LabelObject()
        view=self.window.active_view()
        view.run_command(
            'add_labels', {'regex': self.regex,
                           'end': view.sel()[0].begin()})
        view.run_command('draw_labels', {'key': self.key})


class SublimeMotionRightCommand(SublimeMotionCommand):
    def set_label_gen(self):
        return label_generator_single()

    def labels_adder(self):
        global labels

        self.labels_remover(self.key)

        labels = LabelObject()

        view = self.window.active_view()
        cursor = view.sel()[0].begin()
        beg = cursor
        end = view.line(cursor).end()
        view.run_command(
            'add_labels', {'regex': self.regex, 'beg': beg, 'end': end})
        view.run_command('draw_labels', {'key': self.key})


class SublimeMotionLeftCommand(SublimeMotionCommand):
    def set_label_gen(self):
        return label_generator_single()

    def labels_adder(self):
        global labels

        self.labels_remover(self.key)

        labels = LabelObject()
        group =self.window.active_view()

        view = self.window.active_view()
        cursor = view.sel()[0].begin()
        beg = view.line(cursor).begin()
        end = cursor
        view.run_command(
            'add_labels', {'regex': self.regex, 'beg': beg, 'end': end})
        view.run_command('draw_labels', {'key': self.key})
