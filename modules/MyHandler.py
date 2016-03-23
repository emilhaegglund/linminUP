
# --------------------------------------------------
# File Name: MyHandler.py
# Purpose:
# Creation Date: 2014 - 2015
# Last Modified: Tue Mar  8 22:08:44 2016
# Author(s): The DeepSEQ Team, University of Nottingham UK
# Copyright 2015 The Author(s) All Rights Reserved
# Credits:
# --------------------------------------------------

import os
import time
import datetime
#import hashlib
import multiprocessing
import threading
from Bio import SeqIO
import csv
import numpy as np
import sys
import h5py

from hdf5HashUtils import *
from watchdog.events import FileSystemEventHandler

from checkRead import check_read, check_read_type

from align_dtw import mp_worker
from folderDict import file_dict_of_folder
from processRefFasta import process_ref_fasta_raw
from processFast5 import process_fast5
from processFast5Raw import process_fast5_raw
from exitGracefully import terminateSubProcesses, exitGracefully

# ---------------------------------------------------------------------------
def moveFile(fast5file):
	cmd = ' '.join(["mv",fast5file,fast5file+"bugged"])
	os.system(cmd)


def readFast5File(fast5file):
	try: 
		content = h5py.File(fast5file, 'r')
		return content
	except:
                err_string = "readfast5File(): error ", fast5file
                print >> sys.stderr, err_string
		moveFile(fast5file)
		return ()


class MyHandler(FileSystemEventHandler):

    def __init__(self, dbcheckhash, oper, db, args, xml_file_dict, check_read_args, minup_version):

        self.creates, xml_file_dict = \
		file_dict_of_folder(args, xml_file_dict, args.watchdir)


        self.processed = dict()
        self.running = True

        self.rawcount = dict()
        self.rawprocessed = dict()
        self.p = multiprocessing.Pool(args.procs)
        self.kmerhashT = dict()
        self.kmerhashC = dict()
	self.args = args
	self.oper = oper
	self.db = db
	self.check_read_args = check_read_args
	self.xml_file_dict = xml_file_dict
	self.minup_version = minup_version

        t = threading.Thread(target=self.processfiles)
        t.daemon = True
        
        try:
            t.start()
        except (KeyboardInterrupt, SystemExit):
	    # MS -- Order here is critical ...
            print 'Ctrl-C entered -- exiting'  

	    t.clear() 
            t.stop() 

            self.p.close()  
            self.p.terminate()  
            terminateSubProcesses(args, dbcheckhash, oper, self.minup_version)
            exitGracefully(args, dbcheckhash, self.minup_version)
	    sys.exit(1) 


        if args.ref_fasta is not False:
            fasta_file = args.ref_fasta
            seqlen = get_seq_len(fasta_file)

            # print type(seqlen)

            if args.verbose is True: print seqlen
            shortestSeq = np.min(seqlen.values())
            if args.verbose is True: print shortestSeq
            if args.verbose is True: print args.largerRef

            if not args.largerRef and shortestSeq > 10 ** 8:
                if args.verbose is True: print "Length of references is >10^8: processing may be *EXTREMELY* slow. To overide rerun using the '-largerRef' option"  # MS
                terminateSubProcesses(args, dbcheckhash, oper, self.minup_version)
            elif not args.largerRef and shortestSeq > 10 ** 7:

                if args.verbose is True: print "Length of references is >10^7: processing may be *VERY* slow. To overide rerun using the '-largerRef' option"  # MS
                terminateSubProcesses(args, dbcheckhash, oper, self.minup_version)
            else:

                if args.verbose is True: print 'Length of references is <10^7: processing should be ok .... continuing .... '  # MS

                                                # model_file = "model.txt"
                                                # model_kmer_means=process_model_file(model_file)

	    if args.preproc is True: #  and args.prealign is True:
            	model_file_template = \
			'template.model'
            	model_file_complement = \
               	 	'complement.model'
           	model_kmer_means_template = \
                	process_model_file(args, oper, model_file_template)
            	model_kmer_means_complement = \
                	process_model_file(args, oper, model_file_complement)

                # model_kmer_means = retrieve_model()
                # global kmerhash
                # kmerhash = process_ref_fasta_raw(fasta_file,model_kmer_means)

            	self.kmerhashT = process_ref_fasta_raw(fasta_file,
                    model_kmer_means_template)
            	self.kmerhashC = process_ref_fasta_raw(fasta_file,
                    model_kmer_means_complement)

    def mycallback(self, actions):
	args = self.args
        self.rawprocessed[actions] = time.time()

                                # print self.rawprocessed
                                # print actions

        del self.rawcount[actions]

                                # print self.rawprocessed
                                # print actions

        if args.verbose is True:
            print 'Read Warped'

    def apply_async_with_callback(
        self,
        filename,
        rawbasename_id,
        dbname,
        ):
	args = self.args

                                # print "**** Cursor is",cursor
                                # print "****#------- Raw basename ID =", rawbasename_id

        #print 'Apply Async Called'

                                # print filename
                                # print time.time()

        x = self.p.apply_async(mp_worker, args=((
            filename,
            self.kmerhashT,
            self.kmerhashC,
            time.time(),
            rawbasename_id,
            dbname,
            args,
            ), ), callback=self.mycallback)

                                # x.get()

        if args.verbose is True: print x
        #print 'Call complete'

    def processfiles(self):
	args = self.args
	db = self.db
	oper = self.oper
	xml_file_dict = self.xml_file_dict
	connection_pool, minup_version, \
                comments, ref_fasta_hash, dbcheckhash, \
                logfolder, cursor = self.check_read_args


                                # analyser=RawAnalyser()

        everyten = 0
	customtimeout = 0

                                # if args.timeout_true is not None:
                                #               timeout=args.timeout_true

        while self.running:
            time.sleep(5)
            ts = time.time()
            if args.preproc is True:
                print datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S'
                        ), 'CACHED:', len(self.creates), 'PROCESSED:', \
                    len(self.processed), 'RAW FILES:', \
                    len(self.rawcount), 'RAW WARPED:', \
                    len(self.rawprocessed)
            else:
                print datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S'
                        ), 'CACHED:', len(self.creates), 'PROCESSED:', \
                    len(self.processed)

            if args.customup is True:
                #print "In customup"
                if len(self.creates) > 0:
                    customtimeout=0
                else:
                    customtimeout+=1
                if customtimeout > 6:
		    terminateSubProcesses(args, dbcheckhash, oper, self.minup_version)

            for (fast5file, createtime) in sorted(self.creates.items(), 
						key=lambda x: x[1]):

                # tn=time.time()

                if int(createtime) + 20 < time.time():  
		# file created 20 sec ago, so should be complete ....
                    if fast5file not in self.processed.keys():

                        try:
			  self.hdf = readFast5File(fast5file)
                          self.creates.pop(fast5file, None)
                          self.processed[fast5file] = time.time()
                          # starttime = time.time()


# ##             We want to check if this is a raw read or a basecalled read

                          self.file_type = check_read_type(fast5file,
                                    self.hdf)
		   	  #print str(("file_type: ", self.file_type) )

                            #print "Basecalled Read"
                            #print fast5file
                          if self.file_type > 0 :
                            self.db_name = check_read(
                                    db,
                                    args,
                                    connection_pool,
                                    minup_version,
                                    comments,
                                    xml_file_dict,
                                    ref_fasta_hash,
                                    dbcheckhash,
                                    logfolder,
                                    fast5file,
                                    self.hdf,
                                    cursor,
                                    oper,
                                    )
                            process_fast5(
				    oper,
                                    db,
                                    connection_pool,
                                    args,
                                    ref_fasta_hash,
                                    dbcheckhash,
                                    fast5file,
                                    self.hdf,
                                    self.db_name,
                                    cursor,
                                    )
                          else:
                            #print "Not Basecalled"
                            #print fast5file
                            self.db_name = check_read(
                                    db,
                                    args,
                                    connection_pool,
                                    minup_version,
                                    comments,
                                    xml_file_dict,
                                    ref_fasta_hash,
                                    dbcheckhash,
                                    logfolder,
                                    fast5file,
                                    self.hdf,
                                    cursor,
				    oper,
                                    )
                            self.rawcount[fast5file] = time.time()
                            rawbasename_id = process_fast5_raw(
                                    db,
                                    args,
                                    fast5file,
                                    self.hdf,
                                    self.db_name,
                                    cursor,
                                    )

                            # analyser.apply_async_with_callback(fast5file,rawbasename_id,self.db_name)

			    if args.prealign is True:
                        	print "prealigning", fast5file
                            	x = \
                                    self.apply_async_with_callback(fast5file,
                                        rawbasename_id, self.db_name)
                            	if args.verbose is True: print x  # x.get()
                        	print "prealign finished ", fast5file
			except Exception, err:
			    if self.hdf: # CI
                                self.hdf.close() # CI


                            # print "This is a pre basecalled file"

                            print "MyHandler(): except -- "+ fast5file 
                            err_string = \
                                'Error with fast5 file: %s : %s' \
                                % (fast5file, err)
                            #print >> sys.stderr, err_string
                            print err_string

			'''
                                                                                                #               if dbname is not None:
                                                                                                #                               if dbname in dbcheckhash["dbname"]:
                                                                                                #                                               with open(dbcheckhash["logfile"][dbname],"a") as logfilehandle:
                                                                                                #                                                               logfilehandle.write(err_string+os.linesep)
                                                                                                # s                                                              logfilehandle.close()
			'''

                        everyten += 1
                        if everyten == 10:
                            tm = time.time()
                            if ts + 5 < tm:  # just to stop it printing two status messages one after the other.
                                if args.preproc is True:
                                    print datetime.datetime.fromtimestamp(tm).strftime('%Y-%m-%d %H:%M:%S'
        ), 'CACHED:', len(self.creates), 'PROCESSED:', \
    len(self.processed), 'RAW FILES:', len(self.rawcount), \
    'RAW WARPED:', len(self.rawprocessed)
                                else:
                                    print datetime.datetime.fromtimestamp(tm).strftime('%Y-%m-%d %H:%M:%S'
        ), 'CACHED:', len(self.creates), 'PROCESSED:', \
    len(self.processed)
                            everyten = 0



    def on_created(self, event):
	args = self.args
        if args.preproc is True:
            if 'muxscan' not in event.src_path \
                and event.src_path.endswith('.fast5'):
                self.creates[event.src_path] = time.time()
        else:
            if 'downloads' in event.src_path and 'muxscan' \
                not in event.src_path \
                and event.src_path.endswith('.fast5'):
                self.creates[event.src_path] = time.time()

# ---------------------------------------------------------------------------

def get_seq_len(ref_fasta):
    seqlens = dict()
    for record in SeqIO.parse(ref_fasta, 'fasta'):
        seq = record.seq
        seqlens[record.id] = len(seq)
    return seqlens

#---------------------------------------------------------------------------
'''
def process_model_file(model_file):
    model_kmers = dict()
        reader = csv.reader(csv_file, delimiter='\t')
        d = list(reader)
        for r in range(1, len(d)):
            kmer = d[r][0]
            mean = d[r][1]

                                                # print kmer,mean

            model_kmers[kmer] = mean
    return model_kmers
'''

def process_model_file(args, oper, model_file):
    model_kmers = dict()
    with open(model_file, 'rb') as csv_file:
        reader = csv.reader(csv_file, delimiter="\t")
        d = list(reader)
        for r in range(0, len(d)):
            #print r
            kmer = d[r][0]
            #print kmer
            mean = d[r][1] # args.model_index]
            #print type(mean)
            try:
                if (float(mean) <= 5):
                    print "Looks like you have a poorly formatted model file. These aren't the means you are looking for.\n"
                    print "The value supplied for "+kmer+" was "+str(mean)
		    terminateSubProcesses(args, dbcheckhash, oper, self.minup_version)
            except Exception,err:
                print "Problem with means - but it isn't terminal - we assume this is the header line!"
            #if (args.verbose is True): print kmer, mean
            model_kmers[kmer]=mean
    return     model_kmers


#---------------------------------------------------------------------------
