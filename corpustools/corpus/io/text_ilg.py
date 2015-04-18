
import os
import re
from collections import Counter

from corpustools.corpus.classes import Corpus, Word, Discourse, WordToken, Attribute

from corpustools.exceptions import (DelimiterError, ILGError, ILGLinesMismatchError,
                                ILGWordMismatchError)

from .helper import compile_digraphs, parse_transcription, DiscourseData, AnnotationType,data_to_discourse

def calculate_lines_per_gloss(lines):
    line_counts = [len(x[1]) for x in lines]
    equaled = list()
    for i,line in enumerate(line_counts):
        if i == 0:
            equaled.append(False)
        else:
            equaled.append(line == line_counts[i-1])
    if False not in equaled[1:]:
        #All lines happen to have the same length
        for i in range(2,6):
            if len(lines) % i == 0:
                number = i
    else:
        false_intervals = list()
        ind = 0
        for i,e in enumerate(equaled):
            if i == 0:
                continue
            if not e:
                false_intervals.append(i - ind)
                ind = i
        false_intervals.append(i+1 - ind)
        counter = Counter(false_intervals)
        number = max(counter.keys(), key = lambda x: (counter[x],x))
        if number > 10:
            prev_maxes = set([number])
            while number > 10:
                prev_maxes.add(number)
                number = max(x for x in false_intervals if x not in prev_maxes)
    return number

def inspect_discourse_ilg(path, number = None):
    trans_delimiters = ['.', ';', ',']
    lines = text_to_lines(path, None)
    if number is None:
        number = calculate_lines_per_gloss(lines)
    annotation_types = list()
    for i in range(number):
        if i == 0:
            a = AnnotationType('spelling', None, None, anchor = True, token = False)
        else:
            labels = lines[i][1]
            cat = Attribute.guess_type(labels, trans_delimiters)
            name = 'Line {}'.format(i)
            att = Attribute(Attribute.sanitize_name(name), cat, name)
            if cat == 'tier':
                for l in labels:
                    for delim in trans_delimiters:
                        if delim in l:
                            att.delimiter = delim
                            break
                    if att.delimiter is not None:
                        break
            a = AnnotationType(name, None, annotation_types[0].name, token = False, attribute = att)
        annotation_types.append(a)
    return annotation_types

def characters_discourse_ilg(path):
    pass

def text_to_lines(path, delimiter):
    with open(path, encoding='utf-8-sig', mode='r') as f:
        text = f.read()
        if delimiter is not None and delimiter not in text:
            e = DelimiterError('The delimiter specified does not create multiple words. Please specify another delimiter.')
            raise(e)
    lines = enumerate(text.splitlines())
    lines = [(x[0],x[1].strip().split(delimiter)) for x in lines if x[1].strip() != '']
    return lines

def ilg_to_data(path, annotation_types, delimiter, ignore_list, digraph_list = None,
                    stop_check = None, call_back = None):
    #if 'spelling' not in line_names:
    #    raise(PCTError('Spelling required for parsing interlinear gloss files.'))
    if digraph_list is not None:
        digraph_pattern = compile_digraphs(digraph_list)
    else:
        digraph_pattern = None

    lines = text_to_lines(path, delimiter)

    if len(lines) % len(annotation_types) != 0:
        raise(ILGLinesMismatchError(lines))

    if call_back is not None:
        call_back('Processing file...')
        call_back(0,len(lines))
        cur = 0
    index = 0
    name = os.path.splitext(os.path.split(path)[1])[0]

    data = DiscourseData(name, annotation_types)
    while index < len(lines):
        cur_line = dict()
        for line_ind, annotation_type in enumerate(annotation_types):
            if annotation_type.name == 'ignore':
                continue
            actual_line_ind, line = lines[index+line_ind]
            if len(cur_line.values()) != 0 and len(list(cur_line.values())[-1]) != len(line):
                raise(ILGWordMismatchError((actual_line_ind-1, list(cur_line.values())[-1]),
                                            (actual_line_ind, line)))

            if annotation_type.delimited:
                line = [parse_transcription(x,
                                        annotation_type.attribute.delimiter,
                                        digraph_pattern, ignore_list) for x in line]
            cur_line[annotation_type.name] = line
        for word_name in data.word_levels:
            for i, s in enumerate(cur_line[word_name]):
                annotations = dict()
                word = {'label':s, 'token':dict()}

                for n in data.base_levels:
                    tier_elements = [{'label':x} for x in cur_line[n][i]]
                    level_count = data.level_length(n)
                    word[n] = (level_count,level_count+len(tier_elements))
                    annotations[n] = tier_elements
                for line_type in cur_line.keys():
                    if data[line_type].token:
                        word['token'][line_type] = cur_line[line_type][i]
                    if data[line_type].base:
                        continue
                    if data[line_type].anchor:
                        continue
                    word[line_type] = cur_line[line_type][i]
                annotations[word_name] = [word]
                data.add_annotations(**annotations)
        index += len(annotation_types)
    return data


def load_discourse_ilg(corpus_name, path, annotation_types, delimiter,
                    ignore_list, digraph_list = None,
                    feature_system_path = None,
                    stop_check = None, call_back = None):
    data = ilg_to_data(path, annotation_types, delimiter, ignore_list,
                digraph_list,
                    stop_check, call_back)
    mapping = { x.name: x.attribute for x in annotation_types}
    discourse = data_to_discourse(data, mapping)

    return discourse

def export_discourse_ilg(discourse, path, trans_delim = '.'):
    with open(path, encoding='utf-8', mode='w') as f:
        spellings = list()
        transcriptions = list()
        for wt in discourse:
            spellings.append(wt.spelling)
            transcriptions.append(trans_delim.join(wt.transcription))
            if len(spellings) > 10:
                f.write(' '.join(spellings))
                f.write('\n')
                f.write(' '.join(transcriptions))
                f.write('\n')
                spellings = list()
                transcriptions = list()
        if spellings:
            f.write(' '.join(spellings))
            f.write('\n')
            f.write(' '.join(transcriptions))
            f.write('\n')

