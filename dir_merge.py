import os
import shutil

def merge(dir1, dir2, output_dir):
    print('merging dirs '+dir1 + ' and '+dir2)

    subdirs1 = os.listdir(dir1)
    subdirs2 = os.listdir(dir2)

    index_filepath = os.path.join(output_dir, 'index.txt')
    with open(index_filepath, 'w') as index_file:

        for subdir in subdirs1:
            merge_subdir(subdir, dir1, dir2, output_dir, index_file)
            if subdir in subdirs2:
                subdirs2.remove(subdir)

        for subdir in subdirs2:
            merge_subdir(subdir, dir1, dir2, output_dir, index_file)


def merge_subdir(subdir, dir1, dir2, output_dir, index_file):
    if subdir.startswith('.'):
        print('\tskipping subdir: '+subdir)
        return

    subdir1 = os.path.join(dir1, subdir)
    subdir2 = os.path.join(dir2, subdir)
    output_subdir = os.path.join(output_dir, subdir)

    if os.path.exists(subdir1) and not os.path.exists(subdir2):
        print('\tcopying subdir from 1: '+subdir)
        shutil.copytree(subdir1, output_subdir)
    elif not os.path.exists(subdir1) and os.path.exists(subdir2):
        print('\tcopying subdir from 2: ' + subdir)
        shutil.copytree(subdir2, output_subdir)
    else: #both exist
        print('\tmerging subdir: ' + subdir)
        os.makedirs(output_subdir)

        files1 = os.listdir(subdir1)
        files2 = os.listdir(subdir2)

        for f in files1:
            merge_files(f, subdir1, subdir2, output_subdir)
            if f in files2:
                files2.remove(f)

        for f in files2:
            merge_files(f, subdir1, subdir2, output_subdir)

    merged_files = os.listdir(output_subdir)
    update_index(subdir, merged_files, index_file)


def update_index(case_id, merged_files, index_file):
    has_contents = '0'
    has_headnotes = '0'
    has_cites = '0'
    if 'contents.html' in merged_files:
        has_contents = '1'
    if 'headnotes.html' in merged_files:
        has_headnotes = '1'
    if 'cites.txt' in merged_files:
        has_cites = '1'

    index_file.write(case_id+','+has_contents+','+has_headnotes+','+has_cites+'\n')


def merge_files(filename, dir1, dir2, output_subdir):
    if filename.startswith('.'):
        print('\t\tskipping file '+filename)
        return

    filepath1 = os.path.join(dir1, filename)
    filepath2 = os.path.join(dir2, filename)
    dstpath = os.path.join(output_subdir, filename)

    if os.path.exists(filepath1) and not os.path.exists(filepath2):
        print('\t\tcopying file from 1: ' + filename)
        shutil.copy(filepath1, dstpath)
    elif not os.path.exists(filepath1) and os.path.exists(filepath2):
        print('\t\tcopying file from 2: ' + filename)
        shutil.copy(filepath2, dstpath)
    else:
        if os.path.getsize(filepath1) > os.path.getsize(filepath2):
            print('\t\tcopying file from 1 since its larger: ' + filename)
            shutil.copy(filepath1, dstpath)
        elif os.path.getsize(filepath1) < os.path.getsize(filepath2):
            print('\t\tcopying file from 2 since its larger: ' + filename)
            shutil.copy(filepath2, dstpath)
        else:
            print('\t\tfiles are equal. copying any one: ' + filename)
            shutil.copy(filepath1, dstpath)


if __name__ == '__main__':
    merge('/Users/administrator/Documents/coliee2019/data_fetch/test_files1',
          '/Users/administrator/Documents/coliee2019/data_fetch/test_files2',
          '/Users/administrator/Documents/coliee2019/data_fetch/test_files_merged')