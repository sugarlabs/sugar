/*
Copyright (c) 2007 Bert Freudenberg

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
*/



#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <signal.h>
#include <errno.h>
#include <sys/wait.h>
#include <dbus/dbus.h>
#include <unistd.h>

char* prog;

/* command and arguments for activity instance*/
static char* inst_argv[100];
static int   inst_argc = 0;

/* instance process ids */
static pid_t pidv[100];
static int   pidc = 0;

/* instance process id that exited before it was added */
static pid_t exited = 0;



/* add and remove instances, quit when last instance exits*/

static void
quit()
{
  fprintf(stderr, "%s: quitting\n", prog);
  exit(0);
}


static void
add_pid(pid_t pid)
{
  if (pid == exited)
    {
      fprintf(stderr, "%s: ign instance pid %i\n", prog, pid);
      exited = 0;
      if (pidc == 0)
	quit();
      return;
    }
  pidv[pidc++] = pid;
  fprintf(stderr, "%s: add instance pid %i\n", prog, pid);
}


static void
remove_pid(pid_t pid)
{
  int i;
  for (i=0; i<pidc; i++) 
    if (pidv[i]==pid)
      break;
  if (i==pidc)
    {
      exited = pid;
      return;
    }
  pidc--;
  for ( ; i<pidc; i++)
    pidv[i] = pidv[i+1];

  fprintf(stderr, "%s: del instance pid %i\n", prog, pid);

  if (pidc == 0)
    quit();
}


static void
sigchld_handler(int signum)
{
  int pid;
  int status;
  while (1)
    {
      pid = waitpid(WAIT_ANY, &status, WNOHANG);
      if (pid <= 0)
	break;
      remove_pid(pid);
    }
}



/* fork and exit a new activity instance */

static void
create_instance(int argc)
{
  pid_t pid = fork();
 
  if (pid<0)
    {
      perror("fork failed");
      exit(1);
    }

  inst_argv[argc] = NULL;
  if (pid == 0)
    {
      execvp(inst_argv[0], inst_argv);
      perror(inst_argv[0]);
      exit(1);
    }

  add_pid(pid);
}



/* handle dbus create() call */

static DBusHandlerResult
handle_create(DBusConnection *connection, DBusMessage* message)
{
  DBusMessage *reply;
  DBusMessageIter iter_arss, iter_rss, iter_ss;
  char *key, *value;
  char *activity_id = 0;
  int   argc = inst_argc;

  dbus_message_iter_init(message, &iter_arss);
  if (strcmp("a{ss}", dbus_message_iter_get_signature(&iter_arss)))
    {
      reply = dbus_message_new_error(message, 
				     DBUS_ERROR_INVALID_ARGS, 
				     "signature a{ss} expected");
      dbus_connection_send(connection, reply, NULL);
      dbus_message_unref(reply);
      return DBUS_HANDLER_RESULT_HANDLED;
    }

  dbus_message_iter_recurse(&iter_arss, &iter_rss);

  do
    {
      dbus_message_iter_recurse(&iter_rss, &iter_ss);
      dbus_message_iter_get_basic(&iter_ss, &key);
      dbus_message_iter_next(&iter_ss);
      dbus_message_iter_get_basic(&iter_ss, &value); 

      inst_argv[argc++] = key;
      inst_argv[argc++] = value;

      if (!strcmp("activity_id", key))
	activity_id = value;

    } while(dbus_message_iter_next(&iter_rss));

  if (!activity_id)
    {
      reply = dbus_message_new_error(message, 
				     DBUS_ERROR_INVALID_ARGS, 
				     "'activity_id' expected");
      dbus_connection_send(connection, reply, NULL);
      dbus_message_unref(reply);
      return DBUS_HANDLER_RESULT_HANDLED;
    }

  create_instance(argc);

  reply = dbus_message_new_method_return(message);
  dbus_connection_send(connection, reply, NULL);
  dbus_message_unref(reply);

  return DBUS_HANDLER_RESULT_HANDLED;
}



/* activity factory dbus service */

static void
factory_unregistered_func(DBusConnection  *connection,
			  void            *user_data)
{
}


static DBusHandlerResult
factory_message_func(DBusConnection  *connection,
		     DBusMessage     *message,
		     void            *user_data)
{
  if (dbus_message_is_method_call(message,
				  "org.laptop.ActivityFactory",
				  "create"))
    return handle_create(connection, message);
  else
    return DBUS_HANDLER_RESULT_NOT_YET_HANDLED;
}


static DBusObjectPathVTable
factory_vtable = {
  factory_unregistered_func,
  factory_message_func,
  NULL,
};



/* register service and run main loop */

static char*
dots_to_slashes(char* dotted)
{
    char* slashed = (char*) malloc(strlen(dotted)+2);
    char* p = slashed;
    *p++ = '/';
    strcpy(p, dotted);
    while (*++p) if (*p == '.') *p = '/';
    return slashed;
}


int main(int argc, char **argv)
{
  DBusConnection *connection;
  DBusError error;
  int result;
  int i;
  char* service;
 
  if (argc < 3) 
    {
      printf("Usage: %s org.laptop.MyActivity cmd args\n", argv[0]);
      printf("\twhere cmd will be invoked as\n");
      printf("\tcmd args                           \\\n");
      printf("\t   bundle_id org.laptop.MyActivity \\\n");
      printf("\t   activity_id 123ABC...           \\\n");
      printf("\t   object_id 456DEF...             \\\n");
      printf("\t   pservice_id 789ACE..            \\\n");
      printf("\t   uri file:///path/to/file\n");
      printf("\tas given in the org.laptop.ActivityFactory.create() call\n");
      exit(1);
    }
  prog = argv[0];
  service = argv[1];

  for (i = 2; i<argc; i++)
    inst_argv[inst_argc++] = argv[i];
  inst_argv[inst_argc++] = "bundle_id";
  inst_argv[inst_argc++] = service;
  
  signal(SIGCHLD, sigchld_handler);

  dbus_error_init(&error);

  connection = dbus_bus_get(DBUS_BUS_SESSION, &error);
  if (dbus_error_is_set(&error))
    {
      fprintf(stderr, "%s: could not get bus connection: %s\n", prog, error.message);
      exit(1);
    }

  result = dbus_bus_request_name(connection, 
				 service, 
				 DBUS_NAME_FLAG_DO_NOT_QUEUE, 
				 &error);
  if (dbus_error_is_set(&error))
    {
      fprintf(stderr, "%s: could not aquire name %s: %s\n", prog, service, error.message);
      exit(1);
    }
  if (result != DBUS_REQUEST_NAME_REPLY_PRIMARY_OWNER)
    {
      fprintf(stderr, "%s: could not become primary owner of %s\n", prog, service);
      exit(1);
   }
  
  dbus_connection_register_object_path(connection, 
				       dots_to_slashes(service), 
				       &factory_vtable, 
				       NULL);

  while (dbus_connection_read_write_dispatch(connection, -1))
     ;

  _exit(0);
}
