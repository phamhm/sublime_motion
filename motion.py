from itertools import product
from itertools import permutations
from itertools import chain
from string import digits
from string import ascii_letters
import sublime
import sublime_plugin


class LabelObject:
	def __init__(self):
		self.label_region={}
		self.empty = True

	def add_label_region(self,label,region,displacement):
		if self.empty:
			self.empty = False
		self.label_region[label] = (region,displacement)

	def is_empty(self):
		return self.empty


	def get_region_by_label(self,label):
		if label in self.label_region:
			return self.label_region[label][0]

		return None

		
	def get_region_by_range(self,beg_label, end_label = None):

		if not beg_label:
			return None

		region_list = []
		for label in self.label_region:
			if end_label and label>=beg_label and label<=end_label:
				region_list.append(self.label_region[label])				
			elif not end_label and label>=beg_label:
				region_list.append(self.label_region[label])				

		return region_list

	def get_all_regions(self):
		return [region for region in self.label_region.values()]

	def get_displaced_by_label(self,label):
		if label in self.label_region:
			region,displacement = self.label_region[label]
			region = sublime.Region(region.begin()+displacement,
					region.end()+displacement)
			return region
		return None

	def get_all_displaced_regions(self):
		res =[]
		for region,displacement in self.label_region.values():
			region = sublime.Region(region.begin()+displacement,
					region.end()+displacement)
			res.append(region)
		return res

	def clear(self):
		self.label_region={}
		self.label_list = []
		self.empty = True


def BufferUndoCommand(view,edit,keys):
	"""Command for removing LABELS from views"""
	# print('in undo ',view.sel()[0])
	focus,unfocus=keys
	for key in keys:
		view.erase_regions(key)
	# print('in undo ',view.sel()[0])
	view.end_edit(edit)
	view.run_command("undo")
	# print('in undo ',view.sel()[0])
	
	return True


def AddLabelsCommand(view, edit, regex, labels,label_gen, beg=None,  end=None, literal = False):
	if beg is None:
		beg = view.visible_region().begin()

	if end is None:
		end = view.visible_region().end()

	work_region = sublime.Region(beg, end)

	displacement = 0
	while(beg is not None and beg < end):
		if literal is True:
			region = view.find(regex,beg,sublime.LITERAL)
		else:
			region = view.find(regex,beg)

		if region is not None and not region.empty() and work_region.contains(region):
			label = ''.join(next(label_gen))

			word_region = view.word(region)
			target_size = word_region.end() - word_region.begin()
			while (target_size+displacement)<len(label):
				view.insert(edit, region.end()+displacement ,' ')
				displacement +=1

			replace_region = sublime.Region(
				region.begin(), region.begin() + len(label))
			view.replace(edit,replace_region,label)

			actual_region = sublime.Region(
				region.begin()-displacement, region.begin() + len(label)-displacement)

			labels.add_label_region(label, actual_region, displacement)

			beg = region.end()+displacement
		else:
			return


def JumpToLabelCommand(view, edit, keys, target_point,multiple_selection = False, select_till = False):

	region = sublime.Region(target_point)
	# print('before jump to label',region,view.sel()[0],target_point)

	if select_till is True:
		region_list =[view.sel()[0].begin(),
					view.sel()[0].end(),
					region.begin(),
					region.end()]
		beg = min(region_list)
		end = max(region_list)
		view.sel().add(sublime.Region(beg,end))
		# print('during jump to label',region,view.sel()[0])
	else:
		if not multiple_selection:
			view.sel().clear()
		view.sel().add(region)
		# print('during jump to label',region,view.sel()[0])
	# print('after jump to label',region,view.sel()[0])

	view.show(target_point)


def draw_labels(view,keys,scopes,labels,unfocus_flag,partial_label=None):
	''' 
	'''
	multiple_focuses = True
	matched_region = None
	focus_key,unfocus_key = keys
	focus_scope,unfocus_scope = scopes

	view.erase_regions(focus_key)
	view.erase_regions(unfocus_key)
	
	if not partial_label:
		''' partial label is blank, draw all the labels'''

		view.add_regions(focus_key,
			labels.get_all_displaced_regions(),
			focus_scope)
	else:
		''' 
		partial label is not blank, 
		match all region starts with the partial lable
		'''
		
		focus_list=[]
		unfocus_list=[]
		matched_region = labels.get_region_by_label(partial_label)
		for label in labels.label_region:
			region = labels.get_displaced_by_label(label)
			
			if label.startswith(partial_label):
				focus_list.append(region)
			else:
				unfocus_list.append(region)

		if focus_list:
			''' draw the focus list '''
			view.add_regions(focus_key,focus_list,focus_scope)
			if len(focus_list) == 1:
				multiple_focuses = False

		if unfocus_list:
			''' draw the unfocus list '''
			view.add_regions(unfocus_key,
				unfocus_list,
				unfocus_scope,
				flags=unfocus_flag)

	return (multiple_focuses, matched_region)

def label_generator_singledouble():
	# product =  (tup[0] + tup[1] for tup in permutations(digits+ascii_letters, 2))
	# return chain(ascii_letters,digits,product)
	return chain(ascii_letters,digits[::-1],product(digits+ascii_letters,repeat=2))

def label_generator_double():
	return  (tup[0] + tup[1] for tup in permutations(ascii_letters+digits, 2))
