import argparse
import datetime
import json
import os,sys
import git
import traceback
from tqdm import tqdm

class Progress(git.remote.RemoteProgress):
    def update(self, op_code, cur_count, max_count=None, message=''):
        # Update the progress bar with the current count
        if max_count:
            self.total = max_count
            self.unit = 'B'
            self.unit_scale = True
        else:
            self.total = cur_count
        self.desc = message
        self.update_to(cur_count)


DEST_REPO_DIR = "repo"

def get_file_language(file_extension):
    """
    获取文件扩展名对应的语言类型

    Args:
        file_extension: 文件扩展名

    Returns:
        文件扩展名对应的语言类型
    """
    file_ext = {
        '.py': 'Python',
        '.js': 'JavaScript',
        '.c': 'C',
        '.cpp': 'C++',
        '.java': 'Java',
        '.rb': 'Ruby',
        '.pl': 'Perl',
        '.php': 'PHP',
        '.html': 'HTML',
        '.css': 'CSS',
        '.xml': 'XML',
        '.json': 'JSON',
        '.txt': 'Text',
        '.md': 'Markdown',
        '.sh': 'Shell',
        '.ps1': 'PowerShell',
        '.bat': 'Batch',
        '.swift': 'Swift',
        '.go': 'Go',
        '.r': 'R',
        '.sql': 'SQL',
        '.lua': 'Lua',
        '.dart': 'Dart',
        '.kt': 'Kotlin',
        '.scala': 'Scala',
        '.m': 'Objective-C',
        '.h': 'C/C++ Header',
        '.hpp': 'C++ Header',
        '.cs': 'C#',
        '.vb': 'Visual Basic',
        '.fs': 'F#',
        '.jl': 'Julia',
        '.coffee': 'CoffeeScript',
        '.ts': 'TypeScript',
        '.jsx': 'React JSX',
        '.tsx': 'React TypeScript',
        '.vue': 'Vue.js',
        '.rs': 'Rust',
        '.hs': 'Haskell',
        '.erl': 'Erlang',
        '.clj': 'Clojure',
        '.groovy': 'Groovy',
        '.d': 'D',
        '.asm': 'Assembly',
        '.swift': 'Swift'
    }

    if file_extension.lower() in file_ext:
        return file_ext[file_extension.lower()]
    else:
        return 'Unknown'

def gen_repo_folder_path(repo_url):
    #仓库名字等于作者名字+仓库名字，不然可能会有重名
    repo_folder = f"{repo_url.split('/')[-2]}_{os.path.basename(repo_url).rstrip('.git')}"
    if (len(repo_folder)>4):
        p_folder = os.path.join(DEST_REPO_DIR,repo_folder[:3])
        p_folder = os.path.join(p_folder,repo_folder[1:4])
        # print (repo_folder)
        p_folder = os.path.join(p_folder,repo_folder[2:5])
        repo_folder = os.path.join(p_folder,repo_folder)
        # print (repo_folder)
    else:
        p_folder =  os.path.join(DEST_REPO_DIR,"000_less")
        repo_folder = os.path.join(p_folder,repo_folder)
    # print (repo_folder)
    return repo_folder


def clone_or_pull_repo(repo_url):
    """
    克隆或拉取仓库

    Args:
        repo_url: 仓库URL

    Returns:
        仓库对象
    """
    # 获取仓库名称

    repo_folder = gen_repo_folder_path (repo_url)
    if os.path.exists(repo_folder):
        # 如果本地已经存在仓库，则执行pull操作
        # TODO：这里需要检查如果是仓库没有下载完成，则改成删除重新clone
        repo = git.Repo(repo_folder)
        repo.remotes.origin.pull()
    else:
        # 如果本地不存在仓库，则执行clone操作
        # TODO:多级子目录会不会出错
        # print(f"{repo_url},{repo_folder}")
        repo = git.Repo.clone_from(repo_url, repo_folder,progress=Progress())

    return repo


def get_commits_in_range(repo, start_time, end_time):
    """
    获取指定时间范围内的commit

    Args:
        repo: 仓库对象
        start_time: 开始时间
        end_time: 结束时间

    Returns:
        指定时间范围内的commit列表
    """
    commits = list(repo.iter_commits(since=start_time, until=end_time))
    return commits


def get_diff_content(diff):
    """
    获取diff中的修改内容

    Args:
        diff: diff对象

    Returns:
        diff中的修改内容、添加行数、删除行数和文件扩展名
    """
    diff_a_blob = diff.a_blob
    diff_b_blob = diff.b_blob

    if diff_a_blob is None or diff_a_blob.size > 1048576:
        return None
    

    if diff_b_blob is None or diff_b_blob.size > 1048576:
        return None

    # 将diff内容解码为字符串
    diff_str = diff.diff.decode('utf-8', 'ignore')

    # 统计添加和删除的行数
    added_lines = 0
    deleted_lines = 0
    for line in diff_str.splitlines():
        if line.startswith('+'):
            added_lines += 1
        elif line.startswith('-'):
            deleted_lines += 1

    # 获取文件扩展名
    path = diff.a_path if diff.a_path else diff.b_path
    ext = os.path.splitext(path)[-1]

    return diff_str, added_lines, deleted_lines, ext


def get_commit_logs(repo, start_time, end_time,diff_path):
    """
    获取指定时间范围内的commit的所有diff

    Args:
        repo: 仓库对象
        start_time: 开始时间
        end_time: 结束时间

    Returns:
        指定时间范围内的commit的所有diff列表
    """
    commit_logs = []
    output_jsonl = None
    if diff_path:
        output_jsonl = open(diff_path, "w");

    # 获取指定时间范围内的所有commit
    commits = get_commits_in_range(repo, start_time, end_time)
    for commit in commits:
        diffs = []

        # 获取commit中所有的diff
        for diff in commit.diff(create_patch=True):
            # 获取diff的内容、添加行数、删除行数和文件扩展名
            ret = get_diff_content(diff)
            if not ret :
                continue
            diff_content,addition_count,deletion_count,file_extension = ret
            if diff_content is not None:
                cont = {
                    'addition_count': addition_count,
                    'commit_subject': commit.message,
                    'deletion_count': deletion_count,
                    'file_extension':file_extension,
                    'lang':get_file_language(file_extension),
                    'repo_name':repo.remotes.origin.url,
                    'diff_content': diff_content,
                }
                # 添加diff到列表
                diffs.append(cont)
                if output_jsonl :
                    output_jsonl.write(json.dumps(cont)+ "\n")

        # 将commit的所有diff添加到commit_logs中
        commit_logs.append(diffs)

    if output_jsonl :
        output_jsonl.close()
    return commit_logs


def main():
    # 设置参数解析器
    parser = argparse.ArgumentParser(description='Get commit logs between two dates from a git repository.')
    parser.add_argument('repo_url', type=str, help='URL of the git repository')
    parser.add_argument('--repo_set_dir', type=str,default="repo", help='DEST_REPO_DIR of the repository default=repo')
    parser.add_argument('--diff_filename', default=None,type=str, help='git diff commit jsonl,if null not save')
    parser.add_argument('--start', dest='start_time', type=str, default=(datetime.datetime.now() - datetime.timedelta(days=50*365)).strftime('%Y-%m-%dT%H:%M:%S'),
                        help='start time in the format of "YYYY-MM-DDTHH:MM:SS" (default: 50 years ago)')
    parser.add_argument('--end', dest='end_time', type=str, default=(datetime.datetime.now() + datetime.timedelta(days=1)).strftime('%Y-%m-%dT%H:%M:%S'),
                        help='end time in the format of "YYYY-MM-DDTHH:MM:SS" (default: tomorrow)')

    args = parser.parse_args()
    DEST_REPO_DIR = args.repo_url

    try:
        repo = clone_or_pull_repo(args.repo_url)
        diff_path = None
        if args.diff_filename :
            diff_path = gen_repo_folder_path(args.repo_url)
            diff_path = os.path.join(diff_path,args.diff_filename)

        commit_logs = get_commit_logs(repo, args.start_time, args.end_time,diff_path)
        if not args.diff_filename :
            print(json.dumps(commit_logs, indent=4))
    except Exception as e:
        print(f"Error:{e}",file=sys.stderr)
        # traceback.print_exc()

        exit(-1)



if __name__ == '__main__':
    main()
