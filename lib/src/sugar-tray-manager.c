/* na-tray-manager.c
 * Copyright (C) 2002 Anders Carlsson <andersca@gnu.org>
 * Copyright (C) 2003-2006 Vincent Untz
 *
 * This library is free software; you can redistribute it and/or
 * modify it under the terms of the GNU Lesser General Public
 * License as published by the Free Software Foundation; either
 * version 2 of the License, or (at your option) any later version.
 *
 * This library is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public
 * License along with this library; if not, write to the
 * Free Software Foundation, Inc., 59 Temple Place - Suite 330,
 * Boston, MA 02111-1307, USA.
 *
 * Used to be: eggtraymanager.c
 */

#include <config.h>
#include <string.h>
#include <libintl.h>

#include "sugar-tray-manager.h"

#include <gdkconfig.h>
#include <glib/gi18n.h>
#if defined (GDK_WINDOWING_X11)
#include <gdk/gdkx.h>
#include <X11/Xatom.h>
#elif defined (GDK_WINDOWING_WIN32)
#include <gdk/gdkwin32.h>
#endif
#include <gtk/gtkinvisible.h>
#include <gtk/gtksocket.h>
#include <gtk/gtkwindow.h>

#include "sugar-marshal.h"

/* Signals */
enum
{
  TRAY_ICON_ADDED,
  TRAY_ICON_REMOVED,
  MESSAGE_SENT,
  MESSAGE_CANCELLED,
  LOST_SELECTION,
  LAST_SIGNAL
};

enum {
  PROP_0,
  PROP_ORIENTATION
};

typedef struct
{
  long id, len;
  long remaining_len;
  
  long timeout;
  char *str;
#ifdef GDK_WINDOWING_X11
  Window window;
#endif
} PendingMessage;

static guint manager_signals[LAST_SIGNAL] = { 0 };

#define SYSTEM_TRAY_REQUEST_DOCK    0
#define SYSTEM_TRAY_BEGIN_MESSAGE   1
#define SYSTEM_TRAY_CANCEL_MESSAGE  2

#define SYSTEM_TRAY_ORIENTATION_HORZ 0
#define SYSTEM_TRAY_ORIENTATION_VERT 1

#ifdef GDK_WINDOWING_X11
static gboolean sugar_tray_manager_check_running_screen_x11 (GdkScreen *screen);
#endif

static void sugar_tray_manager_finalize     (GObject      *object);
static void sugar_tray_manager_set_property (GObject      *object,
					  guint         prop_id,
					  const GValue *value,
					  GParamSpec   *pspec);
static void sugar_tray_manager_get_property (GObject      *object,
					  guint         prop_id,
					  GValue       *value,
					  GParamSpec   *pspec);

static void sugar_tray_manager_unmanage (SugarTrayManager *manager);

G_DEFINE_TYPE (SugarTrayManager, sugar_tray_manager, G_TYPE_OBJECT)

static void
sugar_tray_manager_init (SugarTrayManager *manager)
{
  manager->invisible = NULL;
  manager->socket_table = g_hash_table_new (NULL, NULL);
}

static void
sugar_tray_manager_class_init (SugarTrayManagerClass *klass)
{
  GObjectClass *gobject_class;
  
  gobject_class = (GObjectClass *)klass;

  gobject_class->finalize = sugar_tray_manager_finalize;
  gobject_class->set_property = sugar_tray_manager_set_property;
  gobject_class->get_property = sugar_tray_manager_get_property;

  g_object_class_install_property (gobject_class,
				   PROP_ORIENTATION,
				   g_param_spec_enum ("orientation",
						      _("Orientation"),
						      _("The orientation of the tray."),
						      GTK_TYPE_ORIENTATION,
						      GTK_ORIENTATION_HORIZONTAL,
						      G_PARAM_READWRITE | G_PARAM_CONSTRUCT));
  
  manager_signals[TRAY_ICON_ADDED] =
    g_signal_new ("tray_icon_added",
		  G_OBJECT_CLASS_TYPE (klass),
		  G_SIGNAL_RUN_LAST,
		  G_STRUCT_OFFSET (SugarTrayManagerClass, tray_icon_added),
		  NULL, NULL,
		  g_cclosure_marshal_VOID__OBJECT,
		  G_TYPE_NONE, 1,
		  GTK_TYPE_SOCKET);

  manager_signals[TRAY_ICON_REMOVED] =
    g_signal_new ("tray_icon_removed",
		  G_OBJECT_CLASS_TYPE (klass),
		  G_SIGNAL_RUN_LAST,
		  G_STRUCT_OFFSET (SugarTrayManagerClass, tray_icon_removed),
		  NULL, NULL,
		  g_cclosure_marshal_VOID__OBJECT,
		  G_TYPE_NONE, 1,
		  GTK_TYPE_SOCKET);
  manager_signals[MESSAGE_SENT] =
    g_signal_new ("message_sent",
		  G_OBJECT_CLASS_TYPE (klass),
		  G_SIGNAL_RUN_LAST,
		  G_STRUCT_OFFSET (SugarTrayManagerClass, message_sent),
		  NULL, NULL,
		  sugar_marshal_VOID__OBJECT_STRING_LONG_LONG,
		  G_TYPE_NONE, 4,
		  GTK_TYPE_SOCKET,
		  G_TYPE_STRING,
		  G_TYPE_LONG,
		  G_TYPE_LONG);
  manager_signals[MESSAGE_CANCELLED] =
    g_signal_new ("message_cancelled",
		  G_OBJECT_CLASS_TYPE (klass),
		  G_SIGNAL_RUN_LAST,
		  G_STRUCT_OFFSET (SugarTrayManagerClass, message_cancelled),
		  NULL, NULL,
		  sugar_marshal_VOID__OBJECT_LONG,
		  G_TYPE_NONE, 2,
		  GTK_TYPE_SOCKET,
		  G_TYPE_LONG);
  manager_signals[LOST_SELECTION] =
    g_signal_new ("lost_selection",
		  G_OBJECT_CLASS_TYPE (klass),
		  G_SIGNAL_RUN_LAST,
		  G_STRUCT_OFFSET (SugarTrayManagerClass, lost_selection),
		  NULL, NULL,
		  g_cclosure_marshal_VOID__VOID,
		  G_TYPE_NONE, 0);

#if defined (GDK_WINDOWING_X11)
  /* Nothing */
#elif defined (GDK_WINDOWING_WIN32)
  g_warning ("Port SugarTrayManager to Win32");
#else
  g_warning ("Port SugarTrayManager to this GTK+ backend");
#endif
}

static void
sugar_tray_manager_finalize (GObject *object)
{
  SugarTrayManager *manager;
  
  manager = SUGAR_TRAY_MANAGER (object);

  sugar_tray_manager_unmanage (manager);

  g_list_free (manager->messages);
  g_hash_table_destroy (manager->socket_table);
  
  G_OBJECT_CLASS (sugar_tray_manager_parent_class)->finalize (object);
}

static void
sugar_tray_manager_set_property (GObject      *object,
			      guint         prop_id,
			      const GValue *value,
			      GParamSpec   *pspec)
{
  SugarTrayManager *manager = SUGAR_TRAY_MANAGER (object);

  switch (prop_id)
    {
    case PROP_ORIENTATION:
      sugar_tray_manager_set_orientation (manager, g_value_get_enum (value));
      break;
    default:
      G_OBJECT_WARN_INVALID_PROPERTY_ID (object, prop_id, pspec);
      break;
    }
}

static void
sugar_tray_manager_get_property (GObject    *object,
			      guint       prop_id,
			      GValue     *value,
			      GParamSpec *pspec)
{
  SugarTrayManager *manager = SUGAR_TRAY_MANAGER (object);

  switch (prop_id)
    {
    case PROP_ORIENTATION:
      g_value_set_enum (value, manager->orientation);
      break;
    default:
      G_OBJECT_WARN_INVALID_PROPERTY_ID (object, prop_id, pspec);
      break;
    }
}

SugarTrayManager *
sugar_tray_manager_new (void)
{
  SugarTrayManager *manager;

  manager = g_object_new (SUGAR_TYPE_TRAY_MANAGER, NULL);

  return manager;
}

#ifdef GDK_WINDOWING_X11

static gboolean
sugar_tray_manager_plug_removed (GtkSocket       *socket,
			      SugarTrayManager   *manager)
{
  Window *window;

  window = g_object_get_data (G_OBJECT (socket), "na-tray-child-window");

  g_hash_table_remove (manager->socket_table, GINT_TO_POINTER (*window));
  g_object_set_data (G_OBJECT (socket), "na-tray-child-window",
		     NULL);
  
  g_signal_emit (manager, manager_signals[TRAY_ICON_REMOVED], 0, socket);

  /* This destroys the socket. */
  return FALSE;
}

static void
sugar_tray_manager_make_socket_transparent (GtkWidget *widget,
                                         gpointer   user_data)
{
  if (GTK_WIDGET_NO_WINDOW (widget))
    return;

  gdk_window_set_back_pixmap (widget->window, NULL, TRUE);
}

static gboolean
sugar_tray_manager_socket_exposed (GtkWidget      *widget,
                                GdkEventExpose *event,
                                gpointer        user_data)
{
  gdk_window_clear_area (widget->window,
                         event->area.x, event->area.y,
                         event->area.width, event->area.height);
  return FALSE;
}

static void
sugar_tray_manager_socket_style_set (GtkWidget *widget,
                                  GtkStyle  *previous_style,
                                  gpointer   user_data)
{
  if (widget->window == NULL)
    return;

  sugar_tray_manager_make_socket_transparent (widget, user_data);
}

static void
sugar_tray_manager_handle_dock_request (SugarTrayManager       *manager,
				     XClientMessageEvent *xevent)
{
  GtkWidget *socket;
  Window *window;
  GtkRequisition req;

  if (g_hash_table_lookup (manager->socket_table, GINT_TO_POINTER (xevent->data.l[2])))
    {
      /* We already got this notification earlier, ignore this one */
      return;
    }
  
  socket = gtk_socket_new ();

  gtk_widget_set_app_paintable (socket, TRUE);
  //FIXME: need to find a theme where this (and expose event) is needed
  gtk_widget_set_double_buffered (socket, FALSE);

/* FIXME Disabled this so that I can customize the icons background in theme.
   I couldn't find a way to set a specific color for the GtkPlug.
  g_signal_connect (socket, "realize",
                    G_CALLBACK (sugar_tray_manager_make_socket_transparent), NULL);
*/

  g_signal_connect (socket, "expose_event",
                    G_CALLBACK (sugar_tray_manager_socket_exposed), NULL);
  g_signal_connect_after (socket, "style_set",
                          G_CALLBACK (sugar_tray_manager_socket_style_set), NULL);
  
  /* We need to set the child window here
   * so that the client can call _get functions
   * in the signal handler
   */
  window = g_new (Window, 1);
  *window = xevent->data.l[2];
      
  g_object_set_data_full (G_OBJECT (socket),
			  "na-tray-child-window",
			  window, g_free);
  g_signal_emit (manager, manager_signals[TRAY_ICON_ADDED], 0,
		 socket);

  /* Add the socket only if it's been attached */
  if (GTK_IS_WINDOW (gtk_widget_get_toplevel (GTK_WIDGET (socket))))
    {
      g_signal_connect (socket, "plug_removed",
			G_CALLBACK (sugar_tray_manager_plug_removed), manager);
      
      gtk_socket_add_id (GTK_SOCKET (socket), *window);

      g_hash_table_insert (manager->socket_table, GINT_TO_POINTER (*window), socket);

      /*
       * Make sure the icons have a meaningfull size ...
       */ 
      req.width = req.height = 1;
      gtk_widget_size_request (socket, &req);
      /*
      if ((req.width < 16) || (req.height < 16))
      {
          gint nw = MAX (24, req.width);
          gint nh = MAX (24, req.height);
          g_warning (_("tray icon has requested a size of (%i x %i), resizing to (%i x %i)"), 
                      req.width, req.height, nw, nh);
          gtk_widget_set_size_request(icon, nw,  nh);
      }
      */
      gtk_widget_show(socket);
    }
  else
    gtk_widget_destroy (socket);
}

static void
pending_message_free (PendingMessage *message)
{
  g_free (message->str);
  g_free (message);
}

static GdkFilterReturn
sugar_tray_manager_handle_client_message_message_data (GdkXEvent *xev,
                                                    GdkEvent  *event,
                                                    gpointer   data)
{
  XClientMessageEvent *xevent;
  SugarTrayManager       *manager;
  GList               *p;
  int                  len;
  
  xevent  = (XClientMessageEvent *) xev;
  manager = data;

  /* Try to see if we can find the pending message in the list */
  for (p = manager->messages; p; p = p->next)
    {
      PendingMessage *msg = p->data;

      if (xevent->window == msg->window)
	{
	  /* Append the message */
	  len = MIN (msg->remaining_len, 20);

	  memcpy ((msg->str + msg->len - msg->remaining_len),
		  &xevent->data, len);
	  msg->remaining_len -= len;

	  if (msg->remaining_len == 0)
	    {
	      GtkSocket *socket;

	      socket = g_hash_table_lookup (manager->socket_table,
                                            GINT_TO_POINTER (msg->window));

	      if (socket)
		  g_signal_emit (manager, manager_signals[MESSAGE_SENT], 0,
				 socket, msg->str, msg->id, msg->timeout);

	      pending_message_free (msg);
	      manager->messages = g_list_remove_link (manager->messages, p);
              g_list_free_1 (p);
	    }

          break;
	}
    }

  return GDK_FILTER_REMOVE;
}

static void
sugar_tray_manager_handle_begin_message (SugarTrayManager       *manager,
				      XClientMessageEvent *xevent)
{
  GtkSocket      *socket;
  GList          *p;
  PendingMessage *msg;
  long            timeout;
  long            len;
  long            id;

  socket = g_hash_table_lookup (manager->socket_table,
                                GINT_TO_POINTER (xevent->window));
  /* we don't know about this tray icon, so ignore the message */
  if (!socket)
    return;

  /* Check if the same message is already in the queue and remove it if so */
  for (p = manager->messages; p; p = p->next)
    {
      PendingMessage *msg = p->data;

      if (xevent->window == msg->window &&
	  xevent->data.l[4] == msg->id)
	{
	  /* Hmm, we found it, now remove it */
	  pending_message_free (msg);
	  manager->messages = g_list_remove_link (manager->messages, p);
          g_list_free_1 (p);
	  break;
	}
    }

  timeout = xevent->data.l[2];
  len     = xevent->data.l[3];
  id      = xevent->data.l[4];

  if (len == 0)
    {
      g_signal_emit (manager, manager_signals[MESSAGE_SENT], 0,
                     socket, "", id, timeout);
    }
  else
    {
      /* Now add the new message to the queue */
      msg = g_new0 (PendingMessage, 1);
      msg->window = xevent->window;
      msg->timeout = timeout;
      msg->len = len;
      msg->id = id;
      msg->remaining_len = msg->len;
      msg->str = g_malloc (msg->len + 1);
      msg->str[msg->len] = '\0';
      manager->messages = g_list_prepend (manager->messages, msg);
    }
}

static void
sugar_tray_manager_handle_cancel_message (SugarTrayManager       *manager,
				       XClientMessageEvent *xevent)
{
  GList     *p;
  GtkSocket *socket;
  
  /* Check if the message is in the queue and remove it if so */
  for (p = manager->messages; p; p = p->next)
    {
      PendingMessage *msg = p->data;

      if (xevent->window == msg->window &&
	  xevent->data.l[4] == msg->id)
	{
	  pending_message_free (msg);
	  manager->messages = g_list_remove_link (manager->messages, p);
          g_list_free_1 (p);
	  break;
	}
    }

  socket = g_hash_table_lookup (manager->socket_table,
                                GINT_TO_POINTER (xevent->window));
  
  if (socket)
    {
      g_signal_emit (manager, manager_signals[MESSAGE_CANCELLED], 0,
		     socket, xevent->data.l[2]);
    }
}

static GdkFilterReturn
sugar_tray_manager_handle_client_message_opcode (GdkXEvent *xev,
                                              GdkEvent  *event,
                                              gpointer   data)
{
  XClientMessageEvent *xevent;
  SugarTrayManager       *manager;

  xevent  = (XClientMessageEvent *) xev;
  manager = data;

  switch (xevent->data.l[1])
    {
    case SYSTEM_TRAY_REQUEST_DOCK:
      /* Ignore this one since we don't know on which window this was received
       * and so we can't know for which screen this is. It will be handled
       * in sugar_tray_manager_window_filter() since we also receive it there */
      break;

    case SYSTEM_TRAY_BEGIN_MESSAGE:
      sugar_tray_manager_handle_begin_message (manager, xevent);
      return GDK_FILTER_REMOVE;

    case SYSTEM_TRAY_CANCEL_MESSAGE:
      sugar_tray_manager_handle_cancel_message (manager, xevent);
      return GDK_FILTER_REMOVE;
    default:
      break;
    }

  return GDK_FILTER_CONTINUE;
}

static GdkFilterReturn
sugar_tray_manager_window_filter (GdkXEvent *xev,
                               GdkEvent  *event,
                               gpointer   data)
{
  XEvent        *xevent = (GdkXEvent *)xev;
  SugarTrayManager *manager = data;

  if (xevent->type == ClientMessage)
    {
      /* We handle this client message here. See comment in
       * sugar_tray_manager_handle_client_message_opcode() for details */
      if (xevent->xclient.message_type == manager->opcode_atom &&
          xevent->xclient.data.l[1]    == SYSTEM_TRAY_REQUEST_DOCK)
	{
          sugar_tray_manager_handle_dock_request (manager,
                                               (XClientMessageEvent *) xevent);
          return GDK_FILTER_REMOVE;
	}
    }
  else if (xevent->type == SelectionClear)
    {
      g_signal_emit (manager, manager_signals[LOST_SELECTION], 0);
      sugar_tray_manager_unmanage (manager);
    }

  return GDK_FILTER_CONTINUE;
}

#if 0
//FIXME investigate why this doesn't work
static gboolean
sugar_tray_manager_selection_clear_event (GtkWidget         *widget,
                                       GdkEventSelection *event,
                                       SugarTrayManager     *manager)
{
  g_signal_emit (manager, manager_signals[LOST_SELECTION], 0);
  sugar_tray_manager_unmanage (manager);

  return FALSE;
}
#endif
#endif  

static void
sugar_tray_manager_unmanage (SugarTrayManager *manager)
{
#ifdef GDK_WINDOWING_X11
  GdkDisplay *display;
  guint32     timestamp;
  GtkWidget  *invisible;

  if (manager->invisible == NULL)
    return;

  invisible = manager->invisible;
  g_assert (GTK_IS_INVISIBLE (invisible));
  g_assert (GTK_WIDGET_REALIZED (invisible));
  g_assert (GDK_IS_WINDOW (invisible->window));
  
  display = gtk_widget_get_display (invisible);
  
  if (gdk_selection_owner_get_for_display (display, manager->selection_atom) ==
      invisible->window)
    {
      timestamp = gdk_x11_get_server_time (invisible->window);      
      gdk_selection_owner_set_for_display (display,
                                           NULL,
                                           manager->selection_atom,
                                           timestamp,
                                           TRUE);
    }

  //FIXME: we should also use gdk_remove_client_message_filter when it's
  //available
  // See bug #351254
  gdk_window_remove_filter (invisible->window,
                            sugar_tray_manager_window_filter, manager);  

  manager->invisible = NULL; /* prior to destroy for reentrancy paranoia */
  gtk_widget_destroy (invisible);
  g_object_unref (G_OBJECT (invisible));
#endif
}

static void
sugar_tray_manager_set_orientation_property (SugarTrayManager *manager)
{
#ifdef GDK_WINDOWING_X11
  GdkDisplay *display;
  Atom        orientation_atom;
  gulong      data[1];

  if (!manager->invisible || !manager->invisible->window)
    return;

  display = gtk_widget_get_display (manager->invisible);
  orientation_atom = gdk_x11_get_xatom_by_name_for_display (display,
                                                            "_NET_SYSTEM_TRAY_ORIENTATION");

  data[0] = manager->orientation == GTK_ORIENTATION_HORIZONTAL ?
		SYSTEM_TRAY_ORIENTATION_HORZ :
		SYSTEM_TRAY_ORIENTATION_VERT;

  XChangeProperty (GDK_DISPLAY_XDISPLAY (display),
		   GDK_WINDOW_XWINDOW (manager->invisible->window),
                   orientation_atom,
		   XA_CARDINAL, 32,
		   PropModeReplace,
		   (guchar *) &data, 1);
#endif
}

#ifdef GDK_WINDOWING_X11

static gboolean
sugar_tray_manager_manage_screen_x11 (SugarTrayManager *manager,
				   GdkScreen     *screen)
{
  GdkDisplay *display;
  Screen     *xscreen;
  GtkWidget  *invisible;
  char       *selection_atom_name;
  guint32     timestamp;
  
  g_return_val_if_fail (SUGAR_IS_TRAY_MANAGER (manager), FALSE);
  g_return_val_if_fail (manager->screen == NULL, FALSE);

  /* If there's already a manager running on the screen
   * we can't create another one.
   */
#if 0
  if (sugar_tray_manager_check_running_screen_x11 (screen))
    return FALSE;
#endif
  display = gdk_screen_get_display (screen);
  xscreen = GDK_SCREEN_XSCREEN (screen);
  
  invisible = gtk_invisible_new_for_screen (screen);
  gtk_widget_realize (invisible);
  
  gtk_widget_add_events (invisible,
                         GDK_PROPERTY_CHANGE_MASK | GDK_STRUCTURE_MASK);

  selection_atom_name = g_strdup_printf ("_NET_SYSTEM_TRAY_S%d",
					 gdk_screen_get_number (screen));
  manager->selection_atom = gdk_atom_intern (selection_atom_name, FALSE);
  g_free (selection_atom_name);

  sugar_tray_manager_set_orientation_property (manager);
  
  timestamp = gdk_x11_get_server_time (invisible->window);

  /* Check if we could set the selection owner successfully */
  if (gdk_selection_owner_set_for_display (display,
                                           invisible->window,
                                           manager->selection_atom,
                                           timestamp,
                                           TRUE))
    {
      XClientMessageEvent xev;
      GdkAtom             opcode_atom;
      GdkAtom             message_data_atom;

      xev.type = ClientMessage;
      xev.window = RootWindowOfScreen (xscreen);
      xev.message_type = gdk_x11_get_xatom_by_name_for_display (display,
                                                                "MANAGER");

      xev.format = 32;
      xev.data.l[0] = timestamp;
      xev.data.l[1] = gdk_x11_atom_to_xatom_for_display (display,
                                                         manager->selection_atom);
      xev.data.l[2] = GDK_WINDOW_XWINDOW (invisible->window);
      xev.data.l[3] = 0;	/* manager specific data */
      xev.data.l[4] = 0;	/* manager specific data */

      XSendEvent (GDK_DISPLAY_XDISPLAY (display),
		  RootWindowOfScreen (xscreen),
		  False, StructureNotifyMask, (XEvent *)&xev);

      manager->invisible = invisible;
      g_object_ref (G_OBJECT (manager->invisible));
      
      opcode_atom = gdk_atom_intern ("_NET_SYSTEM_TRAY_OPCODE", FALSE);
      manager->opcode_atom = gdk_x11_atom_to_xatom_for_display (display,
                                                                opcode_atom);

      message_data_atom = gdk_atom_intern ("_NET_SYSTEM_TRAY_MESSAGE_DATA",
                                           FALSE);

      /* Add a window filter */
#if 0
      /* This is for when we lose the selection of _NET_SYSTEM_TRAY_Sx */
      g_signal_connect (invisible, "selection-clear-event",
                        G_CALLBACK (sugar_tray_manager_selection_clear_event),
                        manager);
#endif
      /* This is for SYSTEM_TRAY_REQUEST_DOCK and SelectionClear */
      gdk_window_add_filter (invisible->window,
                             sugar_tray_manager_window_filter, manager);
      /* This is for SYSTEM_TRAY_BEGIN_MESSAGE and SYSTEM_TRAY_CANCEL_MESSAGE */
      gdk_display_add_client_message_filter (display, opcode_atom,
                                             sugar_tray_manager_handle_client_message_opcode,
                                             manager);
      /* This is for _NET_SYSTEM_TRAY_MESSAGE_DATA */
      gdk_display_add_client_message_filter (display, message_data_atom,
                                             sugar_tray_manager_handle_client_message_message_data,
                                             manager);
      return TRUE;
    }
  else
    {
      gtk_widget_destroy (invisible);
 
      return FALSE;
    }
}

#endif

gboolean
sugar_tray_manager_manage_screen (SugarTrayManager *manager,
			       GdkScreen     *screen)
{
  g_return_val_if_fail (GDK_IS_SCREEN (screen), FALSE);
  g_return_val_if_fail (manager->screen == NULL, FALSE);

#ifdef GDK_WINDOWING_X11
  return sugar_tray_manager_manage_screen_x11 (manager, screen);
#else
  return FALSE;
#endif
}

#ifdef GDK_WINDOWING_X11

static gboolean
sugar_tray_manager_check_running_screen_x11 (GdkScreen *screen)
{
  GdkDisplay *display;
  Atom        selection_atom;
  char       *selection_atom_name;

  display = gdk_screen_get_display (screen);
  selection_atom_name = g_strdup_printf ("_NET_SYSTEM_TRAY_S%d",
                                         gdk_screen_get_number (screen));
  selection_atom = gdk_x11_get_xatom_by_name_for_display (display,
                                                          selection_atom_name);
  g_free (selection_atom_name);

  if (XGetSelectionOwner (GDK_DISPLAY_XDISPLAY (display),
                          selection_atom) != None)
    return TRUE;
  else
    return FALSE;
}

#endif

gboolean
sugar_tray_manager_check_running (GdkScreen *screen)
{
  g_return_val_if_fail (GDK_IS_SCREEN (screen), FALSE);

#ifdef GDK_WINDOWING_X11
  return sugar_tray_manager_check_running_screen_x11 (screen);
#else
  return FALSE;
#endif
}

char *
sugar_tray_manager_get_child_title (SugarTrayManager      *manager,
				 SugarTrayManagerChild *child)
{
  char *retval = NULL;
#ifdef GDK_WINDOWING_X11
  GdkDisplay *display;
  Window *child_window;
  Atom utf8_string, atom, type;
  int result;
  int format;
  gulong nitems;
  gulong bytes_after;
  guchar *val;

  g_return_val_if_fail (SUGAR_IS_TRAY_MANAGER (manager), NULL);
  g_return_val_if_fail (GTK_IS_SOCKET (child), NULL);
  
  display = gdk_screen_get_display (manager->screen);

  child_window = g_object_get_data (G_OBJECT (child),
				    "na-tray-child-window");

  utf8_string = gdk_x11_get_xatom_by_name_for_display (display, "UTF8_STRING");
  atom = gdk_x11_get_xatom_by_name_for_display (display, "_NET_WM_NAME");

  gdk_error_trap_push ();

  result = XGetWindowProperty (GDK_DISPLAY_XDISPLAY (display),
			       *child_window,
			       atom,
			       0, G_MAXLONG,
			       False, utf8_string,
			       &type, &format, &nitems,
			       &bytes_after, (guchar **)&val);
  
  if (gdk_error_trap_pop () || result != Success)
    return NULL;

  if (type != utf8_string ||
      format != 8 ||
      nitems == 0)
    {
      if (val)
	XFree (val);
      return NULL;
    }

  if (!g_utf8_validate (val, nitems, NULL))
    {
      XFree (val);
      return NULL;
    }

  retval = g_strndup (val, nitems);

  XFree (val);
#endif
  return retval;
}

void
sugar_tray_manager_set_orientation (SugarTrayManager  *manager,
				 GtkOrientation  orientation)
{
  g_return_if_fail (SUGAR_IS_TRAY_MANAGER (manager));

  if (manager->orientation != orientation)
    {
      manager->orientation = orientation;

      sugar_tray_manager_set_orientation_property (manager);

      g_object_notify (G_OBJECT (manager), "orientation");
    }
}

GtkOrientation
sugar_tray_manager_get_orientation (SugarTrayManager *manager)
{
  g_return_val_if_fail (SUGAR_IS_TRAY_MANAGER (manager), GTK_ORIENTATION_HORIZONTAL);

  return manager->orientation;
}
