using System;
using System.Collections;
using System.IO;
using System.Text;
using System.Threading;

using Beagle.Daemon;
using Beagle.Util;

namespace Beagle.Daemon.UrkLogQueryable {

    [QueryableFlavor (Name="UrkLog", Domain=QueryDomain.Local, RequireInotify=false)]
    public class UrkLogQueryable : LuceneFileQueryable {

        private static Logger log = Logger.Get ("UrkLogQueryable");

        private string config_dir, log_dir, icons_dir;

        private int polling_interval_in_seconds = 60;
        
        //private GaimBuddyListReader list = new GaimBuddyListReader ();

        public UrkLogQueryable () : base ("UrkLogIndex")
        {
            config_dir = Path.Combine (PathFinder.HomeDir, ".urk");
            log_dir = Path.Combine (config_dir, "logs");
            icons_dir = Path.Combine (config_dir, "icons");
        }

        /////////////////////////////////////////////////
                    
        private void StartWorker() 
        {    
            if (! Directory.Exists (log_dir)) {
                GLib.Timeout.Add (60000, new GLib.TimeoutHandler (CheckForExistence));
                return;
            }

            log.Info ("Starting urk log backend");

            Stopwatch stopwatch = new Stopwatch ();
            stopwatch.Start ();

            State = QueryableState.Crawling;
            Crawl ();
            State = QueryableState.Idle;

            if (!Inotify.Enabled) {
                Scheduler.Task task = Scheduler.TaskFromHook (new Scheduler.TaskHook (CrawlHook));
                task.Tag = "Crawling ~/.urk/logs to find new logfiles";
                task.Source = this;
                ThisScheduler.Add (task);
            }

            stopwatch.Stop ();

            log.Info ("urk log backend worker thread done in {0}", stopwatch); 
        }
        
        public override void Start () 
        {
            base.Start ();
            
            ExceptionHandlingThread.Start (new ThreadStart (StartWorker));
        }

        /////////////////////////////////////////////////

        private void CrawlHook (Scheduler.Task task)
        {
            Crawl ();
            task.Reschedule = true;
            task.TriggerTime = DateTime.Now.AddSeconds (polling_interval_in_seconds);
        }

        private void Crawl ()
        {
            Inotify.Subscribe (log_dir, OnInotifyNewProtocol, Inotify.EventType.Create);

            // Walk through protocol subdirs
            foreach (string proto_dir in DirectoryWalker.GetDirectories (log_dir))
                CrawlProtocolDirectory (proto_dir);
        }

        private void CrawlNetworkDirectory (string proto_dir)
        {
            Inotify.Subscribe (proto_dir, OnInotifyNewTarget, Inotify.EventType.Create);

            // Walk through accounts
            foreach (string account_dir in DirectoryWalker.GetDirectories (proto_dir))
                CrawlTargetDirectory (account_dir);
        }

        private void CrawlTargetDirectory (string account_dir)
        {
            Inotify.Subscribe (account_dir, OnInotifyNewRemote, Inotify.EventType.Create);

            // Walk through remote user conversations
            foreach (string remote_dir in DirectoryWalker.GetDirectories (account_dir))
                CrawlRemoteDirectory (remote_dir);
        }

        private void CrawlRemoteDirectory (string remote_dir)
        {
            Inotify.Subscribe (remote_dir, OnInotifyNewConversation, Inotify.EventType.CloseWrite);

            foreach (FileInfo file in DirectoryWalker.GetFileInfos (remote_dir))
                if (FileIsInteresting (file.Name))
                    IndexLog (file.FullName, Scheduler.Priority.Delayed);
        }

        /////////////////////////////////////////////////

        private bool CheckForExistence ()
        {
            if (!Directory.Exists (log_dir))
                return true;

            this.Start ();

            return false;
        }

        private bool FileIsInteresting (string filename)
        {
            // Filename must be fixed length, see below
            if (filename.Length < 21 || filename.Length > 22)
                return false;

            // Check match on regex: ^[0-9]{4}-[0-9]{2}-[0-9]{2}\\.[0-9]{6}\\.(txt|html)$
            // e.g. 2005-07-22.161521.txt
            // We'd use System.Text.RegularExpressions if they werent so much more expensive
            return Char.IsDigit (filename [0]) && Char.IsDigit (filename [1])
                && Char.IsDigit (filename [2]) && Char.IsDigit (filename [3])
                && filename [4] == '-'
                && Char.IsDigit (filename [5]) && Char.IsDigit (filename [6])
                && filename [7] == '-'
                && Char.IsDigit (filename [8]) && Char.IsDigit (filename [9])
                && filename [10] == '.'
                && Char.IsDigit (filename [11]) && Char.IsDigit (filename [12])
                && Char.IsDigit (filename [13]) && Char.IsDigit (filename [14])
                && Char.IsDigit (filename [15]) && Char.IsDigit (filename [16])
                && filename [17] == '.'
                &&  (    (filename [18] == 't' && filename [19] == 'x' && filename [20] == 't')
                    ||    (filename [18] == 'h' && filename [19] == 't' && filename [20] == 'm' && filename [21] == 'l')
                    );
        }

        /////////////////////////////////////////////////

        private void OnInotifyNewNetwork (Inotify.Watch watch,
                        string path, string subitem, string srcpath,
                        Inotify.EventType type)
        {
            if (subitem.Length == 0 || (type & Inotify.EventType.IsDirectory) == 0)
                return;

            CrawlNetworkDirectory (Path.Combine (path, subitem));
        }

        private void OnInotifyNewTarget (Inotify.Watch watch,
                        string path, string subitem, string srcpath,
                        Inotify.EventType type)
        {
            if (subitem.Length == 0 || (type & Inotify.EventType.IsDirectory) == 0)
                return;

            CrawlTargetDirectory (Path.Combine (path, subitem));
        }

        private void OnInotifyNewRemote (Inotify.Watch watch,
                        string path, string subitem, string srcpath,
                        Inotify.EventType type)
        {
            if (subitem.Length == 0 || (type & Inotify.EventType.IsDirectory) == 0)
                return;

            CrawlRemoteDirectory (Path.Combine (path, subitem));
        }

        private void OnInotifyNewConversation (Inotify.Watch watch,
                        string path, string subitem, string srcpath,
                        Inotify.EventType type)
        {
            if (subitem.Length == 0 || (type & Inotify.EventType.IsDirectory) != 0)
                return;

            if (FileIsInteresting (subitem))
                IndexLog (Path.Combine (path, subitem), Scheduler.Priority.Immediate);            
        }

        /////////////////////////////////////////////////
        
        private static Indexable IRCLogToIndexable (string filename)
        {
            Uri uri = UriFu.PathToFileUri (filename);
            Indexable indexable = new Indexable (uri);
            indexable.ContentUri = uri;
            indexable.Timestamp = File.GetLastWriteTimeUtc (filename);
            indexable.MimeType = GaimLog.MimeType; // XXX
            indexable.HitType = "IRCLog";
            indexable.CacheContent = false;

            return indexable;
        }

        private void IndexLog (string filename, Scheduler.Priority priority)
        {
            if (! File.Exists (filename))
                return;

            if (IsUpToDate (filename))
                return;

            Indexable indexable = IRCLogToIndexable (filename);
            Scheduler.Task task = NewAddTask (indexable);
            task.Priority = priority;
            task.SubPriority = 0;
            ThisScheduler.Add (task);
        }

        override protected double RelevancyMultiplier (Hit hit)
        {
            return HalfLifeMultiplierFromProperty (hit, 0.25,
                                   "fixme:endtime", "fixme:starttime");
        }

        override protected bool HitFilter (Hit hit) 
        {
            /*ImBuddy buddy = list.Search (hit ["fixme:speakingto"]);
            
            if (buddy != null) {
                if (buddy.Alias != "")
                    hit ["fixme:speakingto_alias"] = buddy.Alias;
                
                //if (buddy.BuddyIconLocation != "")
                //  hit ["fixme:speakingto_icon"] = Path.Combine (icons_dir, buddy.BuddyIconLocation);
            }*/
            
            return true;
        }

    }
}

