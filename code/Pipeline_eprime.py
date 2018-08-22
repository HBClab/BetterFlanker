# generate pipelines that read in the eprime txt files and output a
# machine readable summary and a useful figure for quality assurance.

from convert_eprime import convert
import pandas as pd
import numpy as np
import seaborn as sns
from argparse import ArgumentParser
import os
from matplotlib import pyplot as plt
from glob import glob
import shutil
import re

# style settings for the graphs
plt.style.use('ggplot')
sns.set_palette("bright")

# expressions
session_dict = {1: 'pre', 2: 'post'}


def get_parser():
    """Build parser object for cmdline processing"""
    parser = ArgumentParser(description='task_switch_convert.py: converts '
                                        'eprime output to tsv in BIDS format')
    parser.add_argument('-b', '--bids', action='store',
                        help='root folder of a BIDS valid dataset')
    parser.add_argument('-r', '--raw-dir', action='store',
                        help='directory where edat and txt files live')
    parser.add_argument('-p', '--participant-label', action='store', nargs='+',
                        help='participant label(s) to process')
    parser.add_argument('-s', '--session-label', action='store', nargs='+',
                        help='session label(s) to process (either 1 or 2)')
    parser.add_argument('-c', '--config', action='store', required=True,
                        help='config file to process the eprime txt. '
                             'see convert_eprime for details')
    parser.add_argument('-a', '--acq-id', action='store', choices=['keyboard', 'srbox', 'mri'], required=True,
                        help='the data can either come from a keyboard response, or an srbox response')
    parser.add_argument('--sub-prefix', action='store',
                        help='add additional characters to the prefix of the participant label')
    return parser

def copy_eprime_files(src, dest):
    # collect edat2 and txt files
    types = ('*.edat2', '*.txt')
    raw_files = []
    for type in types:
        raw_files.extend(glob(os.path.join(src, type)))

    # copy all files into sourcedata (if not already there)
    copied_files = 0
    for file in raw_files:
        out_file = os.path.join(dest, os.path.basename(file))
        if not os.path.isfile(out_file):
            shutil.copy(file, dest)
            copied_files += 1
    return copied_files

def main():
    """Entry point"""
    opts = get_parser().parse_args()

    # set input/output directories
    bids_dir = os.path.abspath(opts.bids)
    # ensure bids directory exists
    os.makedirs(bids_dir, exist_ok=True)



    sourcedata = os.path.join(bids_dir, 'sourcedata', 'flanker')
    derivatives = os.path.join(bids_dir, 'derivatives')

    # ensure sourcedata and derivatives exist
    os.makedirs(sourcedata, exist_ok=True)
    os.makedirs(derivatives, exist_ok=True)


    # assume data is already copied over if raw_dir isn't specified
    if opts.raw_dir:
        raw_dir = os.path.abspath(opts.raw_dir)
        # output is only the number of copied files, throwing away
        files_copied = copy_eprime_files(raw_dir, sourcedata)
        print('{num} file(s) copied'.format(num=files_copied))
    else:
        print('-r not specified, assuming data are in the correct location: '
              '{dir}'.format(dir=sourcedata))

    # collect participant labels
    if opts.participant_label:
        participants = opts.participant_label
    else:
        participant_files = glob(os.path.join(sourcedata, 'flankerA*.txt'))
        sub_expr = re.compile(r'^.*flankerA-(?P<sub_id>[0-9]{3})-(?P<ses_id>[0-2])-1.txt')
        participants = []
        for participant_file in participant_files:
            print(participant_file)
            sub_dict = sub_expr.search(participant_file).groupdict()
            participants.append(sub_dict['sub_id'])

    # collect sessions
    if opts.session_label:
        sessions = opts.session_label
    else:
        sessions = [1, 2]

    filename_template = 'flankerA-{sub}-{ses}-1.txt'
    participant_dict = {}
    for participant in participants:
        participant_dict[participant] = {}
        for session in sessions:
            # initialize sub/ses dictionary
            participant_dict[participant][session] = {'edat': None, 'txt': None}
            # get the edat file (if it exists)
            edat_file = filename_template.format(sub=participant, ses=session)

            if os.path.isfile(os.path.join(sourcedata, txt_file)):
                participant_dict[participant][session]['txt'] = os.path.join(
                    sourcedata, txt_file)
            else:
                print('{txt} missing!'.format(txt=txt_file))
                participant_dict[participant].pop(session)
                continue

    # process the data per session
    for participant in participant_dict.keys():
        if opts.sub_prefix:
            participant_label = opts.sub_prefix + participant
        else:
            participant_label = participant
        for session in participant_dict[participant].keys():
            # type coersion to integer
            session = int(session)
            session_label = session_dict[session]
            edat_file = participant_dict[participant][session]['edat']
            txt_file = participant_dict[participant][session]['txt']
            config = os.path.abspath(opts.config)

            work_file = os.path.join(sourcedata, 'work', 'sub-' + participant_label, 'ses-' + session_label,
                                     'beh', 'sub-{sub}_ses-{ses}_task-flanker_raw.csv'.format(sub=participant_label,
                                                                                              ses=session_label))
            # ensure directory exists
            os.makedirs(os.path.dirname(work_file), exist_ok=True)
            # conversion to csv
            convert.text_to_rcsv(txt_file, edat_file, config, work_file)
            #create dataframe
            df = pd.read_csv(work_file)
            #identifies all data recorded from breaks between stimuli
            array = np.where(df['stimuli'] == 'images/fix.bmp')
            #removes data recorded from breaks between stimuli
            df.drop(array[0], inplace=True)
            #removes all rows that are all NaN
            df.dropna(how='all', inplace=True)
            #drops superfulous "stimuli" column
            df.drop(['stimuli'], axis=1, inplace=True)
            #renames columns
            df = df.rename(index=str, columns={"condition": "trial_type", "stimulus.ACC": "correct", "stimulus.RT": "response_time"})
            #converts 'response_time' column to seconds
            df['response_time'] = df['response_time'] / 1000
            #changes 'corrct' column from float to int
            df.correct = df.correct.astype(int)
            #rights df out to csv
            df.to_csv(path_or_buf=proc_file, sep='\t', na_rep="n/a", index=False)
