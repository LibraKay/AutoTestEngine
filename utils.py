# -*- encoding=utf-8 -*-
# based on multi-devices-runner
import argparse
import json
import os
import re
import subprocess
import time
import logging
import traceback
import webbrowser
from jinja2 import Environment, FileSystemLoader

RootPath = os.path.dirname(os.path.abspath(__file__))
BaseLogDir = os.path.join(RootPath, "logs")
ScriptsDir = r"E:\Work_Kay\airscripts\jana.huawei.air"


class Logger:
    def __init__(self, path, clevel=logging.DEBUG, Flevel=logging.DEBUG):
        self.logger = logging.getLogger(path)
        self.logger.setLevel(logging.DEBUG)
        self.fmt = logging.Formatter('[%(asctime)s][%(levelname)s] %(message)s', '%Y-%m-%d %H:%M:%S')
        self.clevel = clevel
        self.Flevel = Flevel
        # 设置CMD日志
        self.sh = logging.StreamHandler()
        self.sh.setFormatter(self.fmt)
        self.sh.setLevel(clevel)

        if path:
            # 设置文件日志
            self.fh = logging.FileHandler(path)
            self.fh.setFormatter(self.fmt)
            self.fh.setLevel(Flevel)
            self.logger.addHandler(self.sh)
            self.logger.addHandler(self.fh)

    def update_filehandler(self, new_path):
        self.logger.removeHandler(self.fh)
        self.fh = logging.FileHandler(new_path)
        self.fh.setFormatter(self.fmt)
        self.fh.setLevel(self.Flevel)
        self.logger.addHandler(self.fh)

    def debug(self, message):
        self.logger.debug(message)

    def info(self, message):
        self.logger.info(message)

    def warn(self, message):
        self.logger.warning(message)

    def error(self, message):
        self.logger.error(message)

    def critical(self, message):
        self.logger.critical(message)


base_log_fpath = os.path.join(BaseLogDir, "base_log.txt")
log_run = Logger(base_log_fpath)


def run_testcase(testname, devices, testcase, AllDone=True):
    """
        Alldone True: run test fully
    """

    test_log_dir = os.path.join(BaseLogDir, testname)
    case_log_dir = os.path.join(test_log_dir, testcase)
    test_case_log = os.path.join(case_log_dir, testcase + "_log.txt")
    os.makedirs(case_log_dir) if not os.path.exists(case_log_dir) else log_run.debug(
        f"testcase {testname}-{testcase} script log's already existsed")
    log_run.update_filehandler(test_case_log)
    if os.path.exists(base_log_fpath):
        os.remove(base_log_fpath)
    # with open(test_case_log, 'w', encoding='utf-8') as log:
    #     start_time = time.time()
    #     log.write(f'start time:{start_time},initial summary script log' + '\n')
    start_time = time.time()
    log_run.debug(f'start time:{start_time},initial summary script log')

    try:
        json_file = os.path.join(BaseLogDir, testname, testcase, 'case_process.json')
        case_process = load_jdon_process(testname, testcase, AllDone)
        tasks = multi_devices_runner(devices, testcase, case_process, case_log_dir, AllDone)
        for task in tasks:
            status = task['process'].wait()
            case_process['tests'][task['device']] = build_device_report(task['testcase'], task['device'], case_log_dir)
            case_process['tests'][task['device']]['status'] = status
            json.dump(case_process, open(json_file, "w"), indent=4)
        build_summary_report(case_process, case_log_dir)
    except:
        log_run.error(f'task failed, please check the logpath: {test_log_dir}')
        traceback.print_exc()


def build_summary_report(data, case_log_dir):
    """
        生成汇总的测试报告
    """
    try:
        summary = {
            'time': "%.3f" % (time.time() - data['start'][-1]),
            'success': [item['status'] for item in data['tests'].values()].count(0),
            'count': len(data['tests'])
        }
        summary.update(data)
        summary['start'] = time.strftime("%Y-%m-%d %H:%M:%S",
                                         time.localtime(data['start'][-1]))
        # log_run.debug(f"currennt work dir:{os.getcwd()}")
        env = Environment(loader=FileSystemLoader(RootPath),
                          trim_blocks=True)
        html = env.get_template('report_tpl.html').render(data=summary)

        summary_report = os.path.join(case_log_dir, 'report.html')
        with open(summary_report, "w", encoding="utf-8") as f:
            f.write(html)
        webbrowser.open(summary_report)
    except:
        log_run.error(f'build summary report failed: {case_log_dir}')
        traceback.print_exc()


def build_device_report(testcase, device, case_log_dir):
    """
        生成一个脚本的测试报告
        Build one test report for one air script
    """
    def result_device_log(log):
        with open(log, 'r', encoding='utf-8') as l:
            content = l.read()
        p1 = re.compile(r'testcaseid:(.+?)"', re.M | re.I)
        p2 = re.compile(r'test result:(.+?)!', re.M | re.I)
        p3 = re.compile(r'"start_time": (.+?),', re.M | re.I)
        p4 = re.compile(r'"end_time": (.+?)}', re.M | re.I)
        device_case_id = p1.search(content).group(1)
        device_case_result = p2.search(content).group(1)
        device_case_start_time = p3.search(content).group(1)
        device_case_end_time = p4.findall(content)[-1]
        log_run.info(f'result:{device};{device_case_id};{device_case_result};{device_case_start_time};{device_case_end_time};')

    try:
        device_log_dir = os.path.join(case_log_dir, device.replace(".", "_").replace(':', '_'))
        os.makedirs(device_log_dir) if not os.path.exists(device_log_dir) else log_run.debug(
            f'build report: device {device} log dir is already existed.')
        case = os.path.join(ScriptsDir, testcase + ".air")
        log = os.path.join(device_log_dir, 'log.txt')
        if os.path.isfile(log):
            result_device_log(log)
            cmd = [
                "airtest",
                "report",
                case,
                "--log_root",
                device_log_dir,
                "--outfile",
                os.path.join(device_log_dir, 'log.html'),
                "--lang",
                "zh",
                "--plugins",
                "poco.utils.airtest.report"
            ]
            ret = subprocess.call(cmd, shell=True)
            return {
                'status': ret,
                'path': os.path.join(device_log_dir, 'log.html')
            }
        else:
            log_run.error(f'log not found:device-{device},case-{case_log_dir}')
    except:
        log_run.error(f'log build failed:device-{device},case-{case_log_dir}')
        traceback.print_exc()
    return {'status': -1, 'path': ''}


def multi_devices_runner(devices, testcase, case_process, case_log_dir, AllDone):
    """
        在多台设备上运行airtest脚本
        Run airtest on multi-device

        如果脚本目录修改为project/testcase.air
        需要修改运行函数以及ScriptsDir，将目录的project作为可变参数（方便作为http请求）传入
    """
    # 单个case，多个devices，每个devices上执行的case作为一个task
    tasks = []
    for device in devices:
        if (not AllDone and device in case_process['tests'] and
                case_process['tests'][device]['status'] == 0):
            log_run.debug(f"device {device} is complete,so skip")
            continue
        device_log_dir = os.path.join(case_log_dir, device.replace(".", "_").replace(':', '_'))
        os.makedirs(device_log_dir) if not os.path.exists(device_log_dir) else log_run.debug(
            f'device {device} log dir is already existed.')
        case = os.path.join(ScriptsDir, testcase + ".air")
        if not os.path.exists(case):
            log_run.error(f'error: case not found!-{case}')
            raise ValueError(f'error: case not found!-{case}')
        cmd = [
            "airtest", "run", case, "--device", "Android:///" + device, "--log", device_log_dir
        ]
        try:
            log_run.debug(f'script runs--device:{device},testcase:{testcase}')
            tasks.append({
                'process': subprocess.Popen(cmd, shell=True),
                'device': device,
                'testcase': testcase
            })
        except:
            log_run.error(f"case running error: device-{device},case-{case}")
            traceback.print_exc()
    return tasks


def load_jdon_process(testname, testcase, AllDone):
    """"
        加载进度
            如果case_process.json存在且AllDone=False，加载进度
            否则，返回一个空的进度数据
        Loading case_process
            if case_process.json exists and AllDone=False, loading progress in case_process.json
            else return an empty data
    """
    case_log = os.path.join(BaseLogDir, testname, testcase)
    json_file = os.path.join(case_log, 'case_process.json')
    if (not AllDone) and os.path.isfile(json_file):
        data = json.load(open(json_file))
        data['start'].append(time.time())
        return data
    else:
        # if os.path.exists(case_log):
        #     shutil.rmtree(case_log)
        return {
            'start': [time.time()],
            'script': testcase,
            'tests': {}
        }


def get_parsed_args():
    args_parser = argparse.ArgumentParser(description="airtest test")
    args_parser.add_argument("--testname",
                             required=True,
                             help="test case name")
    args_parser.add_argument("--testcase",
                             required=True,
                             help="testcase name, separated with ','")
    args_parser.add_argument("--device",
                             required=True,
                             help="device id, separated with ','")
    args_parser.add_argument("--devicetype",
                             required=False, default="Android",
                             help="device type, default Android")
    args_parser.add_argument("--performanceTest",
                             required=False, default=False,
                             help="whether open performance test")
    args = args_parser.parse_args()
    return args



