# Copyright (c) 2020, NVIDIA CORPORATION. All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
#  * Neither the name of NVIDIA CORPORATION nor the names of its
#    contributors may be used to endorse or promote products derived
#    from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS ``AS IS'' AND ANY
# EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
# PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY
# OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.


from concurrent.futures import thread
import os, sys, re, string, operator, math, datetime, time, signal, subprocess, shutil, glob, pkgutil
import params as p
import common_functions as cf 

###############################################################################
# Basic functions and parameters
###############################################################################

def print_usage():
    print ("Usage: run_one_injection.py <inj_mode, app, line, injection_count>")

def get_seconds(td):
    return (td.microseconds + (td.seconds + td.days * 24 * 3600) * 10**6) / float(10**6)

###############################################################################
# Set enviroment variables for run_script
###############################################################################
[stdout_fname, stderr_fname, injection_seeds_file, new_directory] = ["", "", "", ""]
def set_env_variables(inj_mode, app, error_model, icount): # Set directory paths 

    p.set_paths() # update paths 
    global stdout_fname, stderr_fname, injection_seeds_file, new_directory
    
    new_directory = p.app_log_dir[app] + "/logs/" + app + "-mode" + inj_mode + "-icount" + icount
    stdout_fname = new_directory + "/" + p.stdout_file 
    stderr_fname = new_directory + "/" + p.stderr_file
    injection_seeds_file = new_directory + "/" + p.injection_seeds
    if p.verbose: print ("new_directory: " + new_directory)

    cf.set_env(app, False) # False - not the profiler job

    
###############################################################################
# Record result in to a common file. This function uses file-locking such that
# mutliple parallel jobs can run safely write results to the file
###############################################################################
def record_result(inj_mode, app, error_model, cat, pc, inst_type, tid, injBID, runtime, dmesg, value_str, icount):
    
    res_fname = p.app_log_dir[app] + "/results-mode" + inj_mode + str(p.NUM_INJECTIONS) + ".txt"
    
    result_str=inj_mode+':'
    loc=""
    for i in range(0,len(error_model)):
        result_str+=':'+error_model[i]

    #result_str = icount + ";" + kname + ";" + kcount + ";" + iid + ";" + opid 
    #result_str += ";" + bid + ":" + str(pc) + ":" + str(inst_type) + ":" +  str(tid) 
    result_str += "$" + str(pc) + "$" + str(inst_type) + "$" +  str(tid) 
    result_str += "$" + str(injBID) + "$" + str(runtime) + "$" + str(cat) + "$" + "Outcome (" + p.CAT_STR[cat-1] + ")"
    result_str += "$" + str(value_str) 
    result_str += "$" + str(dmesg) + "\n"
    if p.verbose:
        print (result_str)

    has_filelock = False
    if pkgutil.find_loader('lockfile') is not None:
        from lockfile import FileLock
        has_filelock = True
    
    if has_filelock and p.use_filelock:
        lock = FileLock(res_fname)
        lock.acquire() #acquire lock

    rf = open(res_fname, "a")
    rf.write(result_str)
    rf.close()

    if has_filelock and p.use_filelock:
        lock.release() # release lock

    # Record the outputs if 
    if cat == p.OUT_DIFF or cat == p.STDOUT_ONLY_DIFF or cat == p.APP_SPECIFIC_CHECK_FAIL:
        if not os.path.isdir(p.app_log_dir[app] + "/sdcs"): os.system("mkdir -p " + p.app_log_dir[app] + "/sdcs") # create directory to store sdcs 
        full_sdc_dir = p.app_log_dir[app] + "/sdcs/sdc-" + app + "-icount" +  icount
        os.system("mkdir -p " + full_sdc_dir) # create directory to store sdc
        shutil.copytree(new_directory,full_sdc_dir,dirs_exist_ok=True)
        shutil.make_archive(full_sdc_dir, 'gztar', full_sdc_dir) # archieve the outputs
        shutil.rmtree(full_sdc_dir, True) # remove the directory
        if p.verbose:
            print("stdout: "+stdout_fname)
            print("stderr: "+stderr_fname)
            print("inj_file: "+injection_seeds_file)
            print("newdir: "+new_directory+"/" + p.output_diff_log)
            print("sdc_dir: "+full_sdc_dir)

###############################################################################
# Create params file. The contents of this file will be read by the injection run.
###############################################################################
def create_p_file(p_filename, inj_mode, error_mode):
    outf = open(p_filename, "w")

    if inj_mode == 'ICOC':
        for fields in error_mode[:4]:
            outf.write(fields+"\n")
    elif inj_mode=='IRA' or inj_mode=='IR':
        if len(error_mode)==7:
            #threadID=error_mode[0]
            #reg=error_mode[1]
            #mask=error_mode[2]
            #SM=error_mode[3]
            #stuck_at=error_mode[4]
            #outf.write(threadID + "\n" + reg + "\n" + mask + "\n" + SM + "\n" + stuck_at + "\n")
            for fields in error_mode:
                outf.write(fields+"\n")
        else:
            print("Ops... it seems the error descriptor has missing arguments  :(")
    elif inj_mode=='IAT' or inj_mode=='IAW':
        if len(error_mode)==8:
            for fields in error_mode:
                outf.write(fields+"\n")
        else:
            print("Ops... it seems the error descriptor has missing arguments  :(")
    elif inj_mode=='IAC':
        if len(error_mode)==8:
            for fields in error_mode:
                outf.write(fields+"\n")
        else:
            print("Ops... it seems the error descriptor has missing arguments  :(")
    elif inj_mode=='IIO':
        print('Sorry! This error model is not implemented yet, give us a hand ;)')
    else:
        print(f"Ops.. the {inj_mode} error model does not exist, perhaps it is a new model you can implement in the future ;)")	

    outf.close()

###############################################################################
# Parse log file and get the injection information. 
# Example log file contents:
#  index: 2
#  kernel_name: _Z14calculate_tempiPfS_S_iiiiffffff
#  ctas: 7396
#  instrs: 347063509
#  grp 0: 14845260; grp 1: 42084232; grp 2: 21040460; grp 3: 64008930; grp 4: 21939411; grp 5: 183145216; grp 6: 325124098
#  mask: 0x10
#  beforeVal: 0xc0000
#  afterVal: 0xc0010
#  regNo: 3
#  opcode: XMAD
#  pcOffset: 0x90
#  tid: 1201956
###############################################################################
def get_inj_info(inj_mode):
    [value_str, pc, inst_type, tid, injBID] = ["", "", "", -1, -1]
    if os.path.isfile(p.inj_run_log): 
        logf = open(p.inj_run_log, "r")
        if inj_mode in ['ICOC', 'IRA', 'IR', 'IAT', 'IAW', 'IAC']:
            for line in logf:
                if "Report_Summary:" in line:
                    value_str=line.replace("Report_Summary: ;","").strip()
                fields=line.strip().split(';')
                for field in fields:
                    if "LastPCOffset:" in field:
                        pc=field.strip().split(':')[1].strip()
                    if "LastOpcode:" in field:
                        inst_type=field.strip().split(':')[1].strip()
        elif inj_mode=='IIO':
            print('Sorry! This error model is not implemented yet, give us a hand ;)')
        else:
            print(f"Ops.. the {inj_mode} error model does not exist, perhaps it is a new model you can implement in the future ;)")	

        logf.close()

    return [value_str, pc, inst_type, tid, injBID]

###############################################################################
# Classify error injection result based on stdout, stderr, application output,
# exit status, etc.
###############################################################################
def classify_injection(app, inj_mode, error_model, retcode, dmesg_delta):
    #inj_mode, error_mode,
    [found_line, found_error, found_skip] = [False, False, False]

    stdout_str = "" 
    if os.path.isfile(stdout_fname): 
        stdout_str = str(open(stdout_fname).read())

    if p.detectors and "- 43, Ch 00000010, engmask 00000101" in dmesg_delta and "- 13, Graphics " not in dmesg_delta and "- 31, Ch 0000" not in dmesg_delta: # this is specific for error detectors 
        return p.DMESG_XID_43

        # in case an application exits with non-zero exit status be default, we make an exception here. 
    if "bmatrix" in app and "Application Done" not in stdout_str: # exception for the matrixMul app
        if retcode != 0:
            return p.NON_ZERO_EC

    inj_log_str = ""
    if os.path.isfile(p.inj_run_log): 
        inj_log_str = str(open(p.inj_run_log, "r").read())
    
    loc=""
    for i in range(0,len(error_model)):
        loc+=error_model[i]+','

    if "ERROR FAIL Detected Signal SIGKILL" in inj_log_str: 		
        if p.verbose: print (f"Detected SIGKILL: {loc}")
        return p.OTHERS
    if "Error not injected" in inj_log_str or "ERROR FAIL in kernel execution; Expected reg value doesn't match;" in inj_log_str: 
        print (inj_log_str)
        if p.verbose: print (f"Error Not Injected: {loc}" )
        return p.OTHERS
    if "Error: misaligned address" in stdout_str: 
        return p.STDOUT_ERROR_MESSAGE
    if "Error: an illegal memory access was encountered" in stdout_str: 
        return p.STDOUT_ERROR_MESSAGE
    if "Error: misaligned address" in str(open(stderr_fname).read()): # if error is found in the log standard err 
        return p.STDOUT_ERROR_MESSAGE

    os.system(p.script_dir[app] + "/sdc_check.sh") # perform SDC check

    if os.path.isfile(p.output_diff_log) and os.path.isfile(p.stdout_diff_log) and os.path.isfile(p.stderr_diff_log):
        if os.path.getsize(p.output_diff_log) == 0 and os.path.getsize(p.stdout_diff_log) == 0 and os.path.getsize(p.stderr_diff_log) == 0: # no diff is observed
            if "ERROR FAIL in kernel execution" in inj_log_str: 
                return p.MASKED_KERNEL_ERROR # masked_kernel_error
            else:
                if os.path.isfile(p.special_sdc_check_log):
                    if os.path.getsize(p.special_sdc_check_log) != 0:
                        if "Xid" in dmesg_delta:
                            return p.DMESG_APP_SPECIFIC_CHECK_FAIL
                        else:
                            return p.APP_SPECIFIC_CHECK_FAIL
                return p.MASKED_OTHER # if not app specific error, mark it as masked

        if os.path.getsize(p.output_diff_log) != 0:
            if "Xid" in dmesg_delta:
                return p.DMESG_OUT_DIFF 
            elif "ERROR FAIL in kernel execution" in inj_log_str: 
                return p.SDC_KERNEL_ERROR
            else:
                return p.OUT_DIFF 
        elif os.path.getsize(p.stdout_diff_log) != 0 and os.path.getsize(p.stderr_diff_log) == 0:
            if "Xid" in dmesg_delta:
                return p.DMESG_STDOUT_ONLY_DIFF
            elif "ERROR FAIL in kernel execution" in inj_log_str: 
                return p.SDC_KERNEL_ERROR
            else:
                return p.STDOUT_ONLY_DIFF
        elif os.path.getsize(p.stderr_diff_log) != 0 and os.path.getsize(p.stdout_diff_log) == 0:
            if "Xid" in dmesg_delta:
                return p.DMESG_STDERR_ONLY_DIFF
            elif "ERROR FAIL in kernel execution" in inj_log_str: 
                return p.SDC_KERNEL_ERROR
            else:
                return p.STDERR_ONLY_DIFF
        else:
            if p.verbose: 
                print ("Other from here")
            return p.OTHERS
    else: # one of the files is not found, strange
        print ("%s, %s, %s not found" %(p.output_diff_log, p.stdout_diff_log, p.stderr_diff_log))
        return p.OTHERS

def cmdline(command):
    process = subprocess.Popen(args=command, stdout=subprocess.PIPE, shell=True)
    return process.communicate()[0]

###############################################################################
# Check for timeout and kill the job if it has passed the threshold
###############################################################################
def is_timeout(app, pr): # check if the process is active every 'factor' sec for timeout threshold 
    factor = 0.5
    retcode = None
    tt = p.TIMEOUT_THRESHOLD * p.apps[app][3] # p.apps[app][2] = expected runtime
    if tt < 10: tt = 10

    to_th = tt / factor
    while to_th > 0:
        retcode = pr.poll()
        if retcode is not None:
            break
        to_th -= 1
        time.sleep(factor)

    if to_th == 0:
        os.killpg(pr.pid, signal.SIGINT) # pr.kill()
        print ("timeout")
        return [True, pr.poll()]
    else:
        return [False, retcode]

def get_dmesg_delta(dm_before, dm_after):
    llb = dm_before.splitlines()[-1] # last lin
    pos = dm_after.find(llb)
    return str(dm_after[pos+len(llb)+1:])

###############################################################################
# Run the actual injection run 
###############################################################################
def run_one_injection_job(inj_mode, app, error_model, icount):
    start = datetime.datetime.now() # current time
    [pc, inst_type, tid, injBID, ret_vat] = ["", "", -1, -1, -1]

    shutil.rmtree(new_directory, True)
    os.system("mkdir -p " + new_directory) # create directory to store temp_results

    create_p_file(injection_seeds_file, inj_mode, error_model)

    dmesg_before = cmdline("dmesg")

    if p.verbose: print ("%s: %s" %(new_directory, p.script_dir[app] + "/" + p.run_script))
    cwd = os.getcwd()
    os.chdir(new_directory) # go to app dir
    if p.verbose: start_main = datetime.datetime.now() # current time
    cmd = p.script_dir[app] + "/" + p.run_script + " " + p.apps[app][4]
    if p.verbose: print (cmd)
    pr = subprocess.Popen(cmd, shell=True, executable='/bin/bash', preexec_fn=os.setsid) # run the injection job

    [timeout_flag, retcode] = is_timeout(app, pr)
    if p.verbose: print ("App runtime: " + str(get_seconds(datetime.datetime.now() - start_main)))

    # Record kernel error messages (dmesg)
    dmesg_after = cmdline("dmesg")
    dmesg_delta = get_dmesg_delta(dmesg_before, dmesg_after)
    dmesg_delta = dmesg_delta.replace("\n", "; ").replace(":", "-")

    if p.verbose: os.system("cat " + p.stdout_file + " " + p.stderr_file)
    
    value_str = ""
    if timeout_flag:
        [value_str, pc, inst_type, tid, injBID] = get_inj_info(inj_mode)
        ret_cat = p.TIMEOUT 
    else:
        [value_str, pc, inst_type, tid, injBID] = get_inj_info(inj_mode)
        ret_cat = classify_injection(app, inj_mode, error_model, retcode, dmesg_delta)
    
    os.chdir(cwd) # return to the main dir
    # print (ret_cat)

    elapsed = datetime.datetime.now() - start
    record_result(inj_mode, app, error_model, ret_cat, pc, inst_type, tid, injBID, get_seconds(elapsed), dmesg_delta, value_str, icount)

    if get_seconds(elapsed) < 0.5: time.sleep(0.5)
    if not p.keep_logs:
        shutil.rmtree(new_directory, True) # remove the directory once injection job is done
    #print(ret_cat)
    return ret_cat

###############################################################################
# Starting point of the execution
###############################################################################
def main(): 
    # print ("run_one_injection.py: kname=%s, argv[8]=%s" %(sys.argv[5], sys.argv[8])
    # check if paths exit
    if not os.path.isdir(p.NVBITFI_HOME): print ("Error: Regression dir not found!")
    if not os.path.isdir(p.NVBITFI_HOME + "/logs/results"): os.system("mkdir -p " + p.NVBITFI_HOME + "/logs/results") # create directory to store summary

    if len(sys.argv) == 5:
        start= datetime.datetime.now()
        #[inj_mode, igid, bfm, app, kname, kcount, iid, opid, bid, icount] = sys.argv[1:]

        [app, inj_mode, line, icount]=sys.argv[1:]

        error_model=line.strip().split()
        #print(error_model, len(error_model))
        set_env_variables(inj_mode, app, error_model, icount) 
        err_cat = run_one_injection_job(inj_mode, app, error_model, icount) 
        elapsed = datetime.datetime.now() - start
        print ("Inj_count=%s, App=%s, Mode=%s, Time=%f, Outcome: %s" %(icount, app, inj_mode, get_seconds(elapsed), p.CAT_STR[err_cat-1]))
    else:
        print_usage()

if __name__ == "__main__":
    main()
