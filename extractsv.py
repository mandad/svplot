import sys
import os
import csv
import glob

# Opens a file and parses out SV strings
def parse_file(read_file, start_index=0):
    """Return only the SSP values and associated positions from an HSX file"""
    have_ssp = False
    is_start = True
    all_data = []
    cur_data_line = [None] * 6  #Indexes 0=ID, 1=X1, 2=Y1, 3=X2, 4=Y2, 5=SSP
    cur_data_line[0] = start_index

    for line in open(read_file):
        if len(line) > 3:
            string_type = line[:3]
            if string_type == 'POS':
                if not have_ssp:
                    if is_start:
                        cur_data_line[1] = line.split(' ')[3]
                        cur_data_line[2] = line.split(' ')[4][:-2]  #remove \r\n
                        is_start = False
                else:
                    cur_data_line[3] = line.split(' ')[3]
                    cur_data_line[4] = line.split(' ')[4][:-2]  #remove \r\n
                    all_data.append(cur_data_line[:])
                    cur_data_line[0] += 1
                    have_ssp = False

                    # Store last to previous position, to aviod breaks in lines
                    cur_data_line[1] = cur_data_line[3]
                    cur_data_line[2] = cur_data_line[4]
            elif string_type == 'RMB':
                cur_data_line[5] = float(line.split(' ')[7])
                if not is_start:
                    have_ssp = True
    #end for
    return all_data

def write_data(filename, write_data):
    """Write out a data file given a list of values"""
    wfile = open(filename, 'w')
    wfile.write('JID\tX1\tY1\tX2\tY2\tSSP\n')
    wfile.writelines([format_line(write_line) for write_line in write_data])

def format_line(write_line):
    """Format a list with items for a data line to a single string"""
    return '%s\t%s\t%s\t%s\t%s\t%0.2f\n' % tuple(write_line)

def process_single(filename):
    """Handle only a single file"""
    file_data = parse_file(filename)
    write_data(filename[:-3]+'txt', file_data)

def main():
    if len(sys.argv) < 2:
        SystemExit(1)

    look_in = sys.argv[1]
    if look_in.endswith('HSX'):
        process_single(look_in)
    elif look_in == '-d' and len(sys.argv) == 4:
        if os.path.isdir(sys.argv[2]):
            file_data = []
            for cur_file in glob.glob(sys.argv[2]+"*.HSX"):
                file_data.extend(list(parse_file(cur_file)))
            write_data(sys.argv[3], file_data)
        else:
            print 'A directory must be specified after the -d option.'
    else:
        print 'You must specify an HSX file or directory to process.'

if __name__ == '__main__':
    main()