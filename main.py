# -*- encoding=utf-8 -*-
from threading import Thread
from utils import *


def main():
    # 读取参数
    args = get_parsed_args()

    testname = args.testname
    devices = args.device.strip().split(',') if isinstance(args.device, str) else args.device
    testcases = args.testcase.strip().split(',')

    test_log_dir = os.path.join(BaseLogDir, testname)
    if not os.path.exists(test_log_dir):
        os.makedirs(test_log_dir)
    main_log_fpath = os.path.join(test_log_dir, testname + "_log.txt")
    log_main = Logger(main_log_fpath, logging.INFO, logging.INFO)

    main_start_time = time.time()
    log_main.info(f"main_start_time:{main_start_time},device:{devices},testname:{testname},testcase:{testcases}")

    th_allcases = []
    for testcase in testcases:
        case_start_time = time.time()
        log_main.info(f'case_start_time:{case_start_time},testcase:{testcase}')
        thread = Thread(target=run_testcase, args=(testname, devices, testcase))
        thread.start()
        th_allcases.append((testcase, thread))

    for th_tuple in th_allcases:
        th_tuple[1].join()
        case_end_time = time.time()
        log_main.info(f'case_end_time:{case_end_time},testcase:{th_tuple[0]}')

    main_end_time = time.time()
    log_main.info(f'main_end_time:{main_end_time},device:{devices},testname:{testname},testcase:{testcases}')


if __name__ == '__main__':
    main()
