#!/usr/bin/env python

# This is a simple web server for a training record application.
# It's your job to extend it by adding the backend functionality to support
# recording training in an SQL database. You will also need to support
# user access/session control. You should only need to extend this file.
# The client side code (html, javascript and css) is complete and does not
# require editing or detailed understanding, it serves only as a
# debugging/development aid.

# import the various libraries needed
import http.cookies as Cookie   # some cookie handling support
from http.server import BaseHTTPRequestHandler, HTTPServer # the heavy lifting of the web server
import urllib # some url parsing support
import json   # support for json encoding
import sys    # needed for agument handling
import time   # time support

import base64 # some encoding support
import sqlite3 # sql database
import random # generate random numbers
import time # needed to record when stuff happened
import datetime

def random_digits(n):
    """This function provides a random integer with the specfied number of digits and no leading zeros."""
    range_start = 10**(n-1)
    range_end = (10**n)-1
    return random.randint(range_start, range_end)

# The following three functions issue SQL queries to the database.

def do_database_execute(op):
    """Execute an sqlite3 SQL query to database.db that does not expect a response."""
    print(op)
    try:
        db = sqlite3.connect('database.db')
        cursor = db.cursor()
        cursor.execute(op)
        db.commit()
    except Exception as e:
        db.rollback()
    finally:
        db.close()

def do_database_fetchone(op):
    """Execute an sqlite3 SQL query to database.db that expects to extract a single row result. Note, it may be a null result."""
    print(op)
    try:
        db = sqlite3.connect('database.db')
        cursor = db.cursor()
        cursor.execute(op)
        result = cursor.fetchone()
        print(result)
        db.close()
        return result
    except Exception as e:
      print(e)
      return None

def do_database_fetchall(op):
    """Execute an sqlite3 SQL query to database.db that expects to extract a multi-row result. Note, it may be a null result."""
    print(op)
    try:
        db = sqlite3.connect('database.db')
        cursor = db.cursor()
        cursor.execute(op)
        result = cursor.fetchall()
        print(result)
        db.close()
        return result
    except Exception as e:
        print(e)
        return None

# The following build_ functions return the responses that the front end client understands.
# You can return a list of these.

def build_response_message(code, text):
    """This function builds a message response that displays a message
       to the user on the web page. It also returns an error code."""
    return {"type":"message","code":code, "text":text}

def build_response_skill(id,name,gained,trainer,state):
    """This function builds a summary response that contains one summary table entry."""
    return {"type":"skill","id":id,"name":name, "gained":gained,"trainer":trainer,"state":state}

def build_response_class(id, name, trainer, when, notes, size, max, action):
    """This function builds an activity response that contains the id and name of an activity type,"""
    return {"type":"class", "id":id, "name":name, "trainer":trainer, "when":when, "notes":notes, "size":size, "max":max, "action":action}

def build_response_attendee(id, name, action):
    """This function builds an activity response that contains the id and name of an activity type,"""
    return {"type":"attendee", "id":id, "name":name, "action":action}

def build_response_redirect(where):
    """This function builds the page redirection response
       It indicates which page the client should fetch.
       If this action is used, it should be the only response provided."""
    return {"type":"redirect", "where":where}

# The following handle_..._request functions are invoked by the corresponding /action?command=.. request

def handle_login_request(iuser, imagic, content):
    """A user has supplied a username and password. Check if these are
       valid and if so, create a suitable session record in the database
       with a random magic identifier that is returned.
       Return the username, magic identifier and the response action set."""

    response = []

    ## Add code here
    if content: #if content is not empty
        iuser = content.get('username',"")        # Declaring iuser and imagic
        imagic = content.get('password',"")
        if iuser and imagic:
            query = f"""SELECT * FROM users
                    WHERE username = '{iuser}' AND password = '{imagic}'"""
            result = do_database_fetchone(query)
            if result:
                # inserting the fetched data from users to session table
                insert = f"INSERT INTO session (userid, magic) VALUES ({result[0]}, '{result[1]}')"
                do_database_execute(insert)
                success_message = build_response_message(0, f"Welcome {iuser}!")
                response.append(success_message)
                response.append(build_response_redirect("/index.html"))
                return [iuser, imagic, response]
            if not result: # if invalid username and password or one of them is invalid
                error_message = build_response_message(200, "Invalid username and password")
                response.append(error_message)
        else:      # if username and password field are empty
            error_message = build_response_message(100, "Username and password are required")
            response.append(error_message)
    else:       #if content is empty
        error_message = build_response_message(100, "Invalid request")
        response.append(error_message)
    return [iuser, imagic, response]

def handle_logout_request(iuser, imagic, parameters):
    """This code handles the selection of the logout button.
       You will need to ensure the end of the session is recorded in the database
       And that the session magic is revoked."""

    response = []

    ## Add code here
    # Fetching userid from users table
    query1= f"SELECT userid FROM users WHERE username='{iuser}'"
    result2 = do_database_fetchone(query1)
    if result2:
        # deleting user details from session table
        query3= f"DELETE FROM session WHERE userid='{result2[0]}'"
        do_database_execute(query3)
        # redirect to logout page
        response.append(build_response_redirect("/logout.html"))
    else:
        #if user details cannot be fetched then redirect to login page
        response.append(build_response_redirect("/login.html"))
    return [iuser, imagic, response]

def handle_get_my_skills_request(iuser, imagic):
    """This code handles a request for a list of a users skills.
       You must return a value for all vehicle types, even when it's zero."""

    response = []

    ## Add code here
    if not iuser and imagic:
        response.append(build_response_redirect('/login.html'))
        return [iuser,imagic, response]
    if iuser and imagic:
        user_id=do_database_fetchone(f"SELECT userid FROM users WHERE username='{iuser}'")[0]
        skills_passed=do_database_fetchall(f""" SELECT s.skillid,s.name,u.fullname,c.start
                                           FROM skill s
                                           INNER JOIN class c ON c.skillid=s.skillid
                                           INNER JOIN attendee a ON a.classid=c.classid
                                           INNER JOIN users u ON u.userid=c.trainerid
                                           WHERE u.userid={user_id} AND a.status=1 ORDER BY c.start ASC
                                           LIMIT 1""")
        if skills_passed:
            for skill_res in skills_passed:
                skill_id,name,trainer,gained=skill_res
                response.append(build_response_skill(skill_id, name, gained,
                                                     trainer, state="passed"))
        else:
            response.append(build_response_message(0, "Noone passed"))
        skills_enrolled=do_database_fetchall(f"""SELECT s.skillid,s.name,u.fullname,c.start
                                             FROM skill s
                                             INNER JOIN class c ON c.skillid=s.skillid
                                             INNER JOIN attendee a ON a.classid=c.classid
                                             INNER JOIN users u ON u.userid=c.trainerid
                                             WHERE a.userid={user_id}
                                             AND c.start>{int(time.time())} AND a.status=0""")
        if skills_enrolled:
            for skill_res1 in skills_enrolled:
                skill_id,name,trainer,gained=skill_res1
                response.append(build_response_skill(skill_id, name, gained,
                                                     trainer, state="scheduled"))
        else:
            response.append(build_response_message(0, "No scheduled skill"))
        skills_failed=do_database_fetchall(f"""SELECT s.skillid,s.name,u.fullname,c.start
                                           FROM skill s
                                           INNER JOIN class c ON c.skillid=s.skillid
                                           INNER JOIN attendee a ON a.classid=c.classid
                                           INNER JOIN users u ON u.userid=c.trainerid
                                           WHERE a.userid={user_id} AND a.status=2
                                           ORDER BY c.start DESC""")
        if skills_failed:
            for skill_res2 in skills_enrolled:
                skill_id,name,trainer,gained=skill_res2
                response.append(build_response_skill(skill_id, name, gained,
                                                     trainer, state="failed"))
        else:
            response.append(build_response_message(0, "Noone failed"))
        skills_trainer=do_database_fetchall(f"""SELECT s.skillid,s.name,u.fullname,c.start
                                            FROM skill s
                                            INNER JOIN class c ON c.skillid=s.skillid
                                            INNER JOIN trainer t ON t.skillid = c.skillid
                                            INNER JOIN users u ON u.userid=t.trainerid
                                            WHERE t.trainerid={user_id}""")
        if skills_trainer:
            for skill_res3 in skills_trainer:
                skill_id,name,trainer,gained=skill_res3
                response.append(build_response_skill(skill_id, name, gained,
                                                     trainer, state="trainer"))
        else:
            response.append(build_response_message(0, "Success"))
    else:
        response.append(build_response_message(210, "Missing parameter"))
    return [iuser, imagic, response]

def handle_get_upcoming_request(iuser, imagic):

    """This code handles a request for the details of a class.
       """

    response = []

    ## Add code here
    if not iuser :
        response.append(build_response_redirect("login.html"))
        return [iuser, imagic, response]
    user_id=do_database_fetchone(f"SELECT userid FROM users WHERE username='{iuser}'")[0]
    res20=do_database_fetchall(f"""SELECT * FROM class
                               WHERE start>{int(time.time())}
                               ORDER BY start ASC """)
    if res20 is not None :
        for class_info in res20:
            class_id,trainer_id,skill_id,start, max_size,notes=class_info
            size=do_database_fetchone(f"""SELECT COUNT(*) FROM attendee
                                      WHERE classid={class_id};""")[0]
            skill_name=do_database_fetchone(f"""SELECT s.name FROM skill s INNER JOIN
                                            class c ON c.skillid=s.skillid
                                            WHERE c.skillid={skill_id};""")[0]
            trainer_name=do_database_fetchone(f"""SELECT u.fullname FROM users u
                                              INNER JOIN attendee a ON a.userid=u.userid
                                              WHERE u.username='{iuser}';""")[0]
            if trainer_id==user_id:
                action='edit'
            else:
                res25=do_database_fetchone(f"""SELECT * FROM attendee
                                           WHERE userid={user_id} AND classid={class_id}
                                           AND status=0 ;""")
                if res25:
                    if start > int(time.time()):
                        action='leave'
                else :
                    res26=do_database_fetchall(f"""SELECT * FROM class c
                                               INNER JOIN attendee a ON c.classid=a.classid
                                               WHERE a.userid={user_id}
                                               AND c.skillid={skill_id} AND a.classid={class_id}
                                               AND a.status IN (1, 2, 3);""")
                    if res26:
                        res27=do_database_fetchall(f"""SELECT * FROM class WHERE classid=
                                                   (SELECT classid FROM attendee WHERE userid = {user_id}
                                                    AND status IN (0,1,3))
                                                   AND skillid = {skill_id};""")
                        if not res27:
                            action='join'
                        else:
                            action='unavailable'
                    else:
                        action = 'unavailable'

            response.append(build_response_class(class_id, skill_name,
                                                 trainer_name, start, notes,
                                                 size, max_size, action))
        response.append(build_response_message(0,"Success"))

    else:
        response.append(build_response_message(106, "No upcoming class found"))



    return [iuser, imagic, response]

def handle_get_class_detail_request(iuser, imagic, content):
    """This code handles a request for a list of upcoming classes.
       """

    response = []

    ## Add code here

    if not iuser : #if not user

        response.append(build_response_redirect("/login.html"))

        return [iuser, imagic, response]

    if 'id' not in content:
        response.append(build_response_message(100, "Missing parameter"))
        return [iuser, imagic, response]

    class_id = content.get('id')

    user_id =do_database_fetchone(f"SELECT userid FROM users WHERE username='{iuser}';")[0]

    trainer_id =do_database_fetchone(f""" SELECT trainerid from class
                                     WHERE trainerid={user_id}
                                     AND classid = {class_id};""")


    if trainer_id: #if user is trainer
        class_details = do_database_fetchone(f"""SELECT classid,skillid,start,max,note
                                             FROM class WHERE classid={class_id};""")
        if class_details:
            class_id,skill_id,when,max_s,notes=class_details
            size1=do_database_fetchone(f"""SELECT COUNT(*) FROM attendee
                                       WHERE classid={class_id};""")[0]         ###
            skill_name=do_database_fetchone(f"""SELECT s.name FROM skill s
                                            INNER JOIN class c ON c.skillid=s.skillid
                                            WHERE c.skillid={skill_id};""")[0]
            trainer_name=do_database_fetchone(f"""SELECT u.fullname FROM users u
                                              INNER JOIN attendee a ON a.userid=u.userid
                                              WHERE u.username='{iuser}';""")[0]

            response.append(build_response_class(class_id, skill_name, trainer_name,when,
                                                 notes, size1, max_s, action='cancel'))

            attendee_details = do_database_fetchall(f"""SELECT a.attendeeid,u.fullname,
                                                    a.status,c.start
                                                    FROM attendee a
                                                    INNER JOIN users u ON u.userid=a.userid
                                                    INNER JOIN class c ON c.classid=a.classid
                                                    WHERE a.classid={class_id};""")
            for attendee in attendee_details:

                attendee_id, name ,status,start= attendee

                if start>int(time.time()) and status==0:
                    response.append(build_response_attendee(attendee_id, name, "remove"))

                if status==0 and start<=int(time.time()):
                    response.append(build_response_attendee(attendee_id, name, "update"))

                if status==1:
                    response.append(build_response_attendee(attendee_id, name, "passed"))

                if status==2:
                    response.append(build_response_attendee(attendee_id, name, "failed"))

                if status==3 and status==4:
                    response.append(build_response_attendee(attendee_id, name, "cancelled"))
                response.append(build_response_message(0, "Successfully getting class detail"))
        else:
            response.append(build_response_message(240, "class not found"))
    else:

        response.append(build_response_message(237, "No attendees"))

    return [iuser, imagic, response]


def handle_join_class_request(iuser, imagic, content):
    """This code handles a request by a user to join a class.
      """
    response = []

    ## Add code here
    if not iuser :
        response.append(build_response_redirect("login.html"))
        return [iuser, imagic, response]
    if 'id' not in content:
        response.append(build_response_message(100, "Missing parameter"))
        return [iuser, imagic, response]
    if iuser and imagic and content:
        user_id =do_database_fetchone(f"SELECT userid FROM users WHERE username='{iuser}'")[0]
        class_id = content.get("id")
        exist_class = do_database_fetchone(f"SELECT classid FROM class WHERE classid = {class_id}")
        size2=do_database_fetchone(f"""SELECT COUNT(*) FROM attendee
                                   WHERE classid={class_id} AND attendee.status = 0;""")[0]
        check_attendee = do_database_fetchone(f"""SELECT * FROM attendee WHERE userid = {user_id}
                                              AND classid = {class_id} AND status IN (1, 0);""")

        if class_id is not None:
            if exist_class is None:
                response.append(build_response_message(250, "Non existing class."))
            elif check_attendee:
                response.append(build_response_message(210,
                                                        """You have been removed
                                                        from the class so you cannot join"""))
            elif not check_attendee:
                max_siz = do_database_fetchone(f"""SELECT max FROM class
                                               WHERE classid = {class_id};""")[0]
                if size2==max_siz:
                    response.append(build_response_message(214, "Class is full"))
                if size2<max_siz:
                    removed_ones = do_database_fetchone(f"""SELECT * FROM attendee
                                                        WHERE userid = {user_id}
                                                        AND classid = {class_id}
                                                        AND status = 4;""")

                    if not removed_ones:
                        # Perform the join operation
                        do_database_execute(f"""INSERT INTO attendee (userid, classid, status)
                                            VALUES ({user_id}, {class_id}, 0);""")
                        response.append(build_response_message(0, "Successfully joined the class!"))
                        class_details = do_database_fetchall(f"""SELECT classid,skillid,start,max,note
                                                             FROM class
                                                             WHERE classid={class_id}""")
                        for class_inf in class_details:
                            classid,skill_id,start,max_siz,notes=class_inf
                            skill_name=do_database_fetchone(f"""SELECT s.name FROM skill s
                                                            INNER JOIN class c ON c.skillid=s.skillid
                                                            WHERE c.classid = {class_id};""")[0]
                            trainer_name=do_database_fetchone(f"""SELECT u.fullname FROM users u
                                                              INNER JOIN attendee a ON a.userid=u.userid
                                                              WHERE u.username='{iuser}';""")[0]

                            response.append(build_response_class(classid, skill_name,
                                                                 trainer_name,
                                                                 start, notes,
                                                                 size2+1, max_siz, 'leave'))
    else:
        response.append(build_response_message(221,"Cannot join this class"))


    return [iuser, imagic, response]

def handle_leave_class_request(iuser, imagic, content):
    """This code handles a request by a user to leave a class.
    """
    response = []

    ## Add code here

    if not iuser :

        response.append(build_response_redirect("login.html"))

        return [iuser, imagic, response]

    if 'id' not in content:
        response.append(build_response_message(100, "Missing parameter"))
        return [iuser, imagic, response]


    if iuser and imagic and content:
        user_id =do_database_fetchone(f"SELECT userid FROM users WHERE username='{iuser}'")[0]

        class_id = content.get("id")


        class_details = do_database_fetchone(f"SELECT * FROM class WHERE classid={class_id}")

        start, max_s, notes = class_details[3:]
        if class_details:
            if start>int(time.time()):
                size=do_database_fetchone(f"""SELECT COUNT(*) FROM attendee
                                          WHERE classid={class_id}""")[0]
                do_database_execute(f"""DELETE FROM attendee
                                    WHERE userid={user_id}
                                    AND classid = {class_id} and status=0""")


                class_fetch = do_database_fetchone(f"""SELECT s.name, u.fullname FROM skill s
                                                   INNER JOIN class c ON c.skillid = s.skillid
                                                       INNER JOIN users u ON u.userid = c.trainerid
                                                       WHERE c.classid = {class_id}""")
                skill_name, trainer_name = class_fetch
                response.append(build_response_class(class_id, skill_name, trainer_name,
                                                     start, notes, size-1, max_s, 'join'))

                response.append(build_response_message(0, "user left"))
            else:
                response.append(build_response_message(200, "Not left"))

    return [iuser, imagic, response]


def handle_cancel_class_request(iuser, imagic, content):
    """This code handles a request to cancel an entire class."""

    response = []

    ## Add code here

    if not iuser :

        response.append(build_response_redirect("/login.html"))

        return [iuser, imagic, response]

    if 'id' not in content:
        response.append(build_response_message(100, "Missing parameter"))
        return [iuser, imagic, response]

    class_id = content.get('id')



    user_id =do_database_fetchone(f"SELECT userid FROM users WHERE username='{iuser}'")[0]
    session_id=do_database_fetchone(f"SELECT sessionid FROM session WHERE userid={user_id} ")[0]
    res51 =do_database_fetchone(f""" SELECT trainerid,start from class
                                WHERE classid = {class_id}""")
    if res51 is None:
        response.append(build_response_message(260,"You are not the trainer of this class."))
    else:

        trainer_id,start=res51
        if session_id is not None:
            if trainer_id == user_id and start>int(time.time()):
                do_database_execute("UPDATE attendee SET status=3 WHERE classid={class_id} ")
                do_database_execute("UPDATE class SET max=0 WHERE classid={class_id}")

                attendee_updated=do_database_fetchall(f"""SELECT a.attendeeid , u.fullname
                                                      FROM attendee a
                                                      INNER JOIN users u ON u.userid=a.userid
                                                      WHERE a.classid={class_id} AND a.status=3 """)
                for attendee in attendee_updated:
                    attendee_id,name=attendee
                    response.append(build_response_attendee(attendee_id, name, "cancelled"))

                    # res32=do_database_fetchall(f"SELECT a.userid,u.fullname,a.status
                    #FROM attendee a INNER JOIN users u ON a.userid=u.userid
                    # WHERE a.classid={class_id} ;" )

                class_details = do_database_fetchone(f"""SELECT classid,skillid,start,note
                                                     FROM class WHERE classid={class_id}""")
                if class_details:
                    class_id,skill_id,start,notes=class_details
                    skill_name=do_database_fetchone(f"""SELECT s.name FROM skill s INNER JOIN class c
                                                    ON c.skillid=s.skillid
                                                    WHERE c.skillid={skill_id};""")
                    trainer_name=do_database_fetchone(f"""SELECT u.fullname FROM users u
                                                      INNER JOIN attendee a ON a.userid=u.userid
                                                      WHERE u.username='{iuser}';""")
                    response.append(build_response_class(class_id, skill_name, trainer_name,
                                                         start, notes, 0, 0, "cancelled"))

                response.append(build_response_message(0,"Successful"))
            else:
                response.append(build_response_message(207, "Not a trainer"))
        else:
            response.append(build_response_redirect("/login.html"))
        # response.append(build_response_message(250, "Bad parameter"))
    return [iuser, imagic, response]

def handle_update_attendee_request(iuser, imagic, content):
    """This code handles a request to cancel a user attendance at a class by a trainer"""

    response = []

    ## Add code here

    if not iuser :

        response.append(build_response_redirect("login.html"))

        return [iuser, imagic, response]


    if iuser:

        attendee_id=content.get("id")
        state=content.get("state")
        res61=do_database_fetchone(f"SELECT * FROM attendee WHERE attendeeid={attendee_id}")
        if res61:

            class_id,current_state=res61[2:4]

            user_id =do_database_fetchone(f"SELECT userid FROM users WHERE username='{iuser}'")[0]

            trainer_id =do_database_fetchone(f""" SELECT trainerid from class WHERE classid =
                                             (SELECT classid FROM attendee 
                                              WHERE userid={user_id})""")[0]
            if trainer_id == user_id:
                class_details = do_database_fetchone(f"""SELECT * FROM class
                                                     WHERE classid={class_id}""")


                start=class_details[3]

                if ((current_state==0 and state=="pass") or (current_state==0 and state=="fail")) :
                    if start > int(time.time()):
                        response.append(build_response_message(255, "The class hasn't started yet."))
                    else:
                        if state == 'pass':
                            state_code = 1

                        else:
                            state_code=2

                        do_database_execute(f"""UPDATE attendee
                                            SET status = {state_code}
                                            WHERE attendeeid = {attendee_id}""")

                        a_name = do_database_fetchone(f"""SELECT fullname FROM users
                                                      WHERE userid = {attendee_id}""")
                        if state_code == 2:
                            action = 'failed'
                        else:
                            action='passed'
                        response.append(build_response_attendee(attendee_id, a_name, action))
                        #response.append(build_response_message(0, "Success"))
                else:
                    if start <= int(time.time()):
                        response.append(build_response_message(256, "The class has finished."))
                        if current_state == 0 and state == 'remove':
                            do_database_execute(f"""UPDATE attendee SET status = 4
                                                WHERE attendeeid = {attendee_id}""")

                            u_name = do_database_fetchone(f"""SELECT fullname FROM users
                                                        WHERE userid = {attendee_id}""")
                            response.append(build_response_attendee(attendee_id, u_name, 'cancelled'))

                            fetch_class = do_database_fetchone(f"""SELECT s.name, u.fullname,
                                                            c.start,c.note, c.max
                                                            FROM class c
                                                            JOIN skill s ON c.skillid = s.skillid
                                                            JOIN users u ON c.trainerid = u.userid
                                                            WHERE c.classid = {class_id}""")

                            current_size = do_database_fetchone(f"""SELECT COUNT(*) FROM attendee
                                                                WHERE classid = {class_id}""")[0]

                            if fetch_class is not None:
                                skill_name, trainer_name, start2, note, max_siz = fetch_class
                                response.append(build_response_class(class_id,skill_name,
                                                                    trainer_name, start2,
                                                                    note, current_size-1,
                                                                    max_siz, 'cancelled'))
                        #response.append(build_response_message(0, "Successfully attendee removed"))
            else:
                response.append(build_response_message(204, "Not a trainer"))


    return [iuser, imagic, response]

def handle_create_class_request(iuser, imagic, content):
    """This code handles a request to create a class."""

    response = []

    ## Add code here
    if not iuser:
        response.append(build_response_redirect('/login.html'))
        return [iuser, imagic, response]
    if iuser and imagic and content:


        userid = do_database_fetchone(f"SELECT userid FROM users WHERE username = '{iuser}'")[0]
        skill_id = int(content.get('id'))
        note = content.get('note')
        max_size = int(content.get('max'))
        day = int(content.get('day'))
        month = content.get("month")
        minute = int(content.get('minute'))
        year = int(content.get('year'))
        hour = int(content.get('hour'))

        skill_exist = do_database_fetchone(f"""SELECT skillid, trainerid FROM trainer
                                          WHERE skillid = {skill_id} and trainerid = {userid}""")  
        if note is None:
            response.append(build_response_message(101, "Missing note"))
        else:
            if skill_exist is None:
                response.append(build_response_message(270, "You are not the trainer of this class")) 
            else:
                try:
                    start_datetime = datetime.datetime(year,month,day,hour,minute)
                    if start_datetime <= datetime.datetime.now():
                        raise ValueError("Date and time should be in future")
                except ValueError as e:
                    response.append(build_response_message(236, str(e)))
                    return [iuser, imagic, response]
        
                skill_query= do_database_fetchone(f"SELECT skillid FROM trainer WHERE skillid = {skill_id}")
                if not skill_query:
                    response.append(build_response_message(220, "Invalid skill details."))
                    return [iuser, imagic, response]
                    
                try:
                    start_datetim = int(start_datetime.timestamp())
                    print('skill',skill_exist[1])
                    do_database_execute(f"""INSERT INTO class (trainerid,skillid,start,max,note)
                                        VALUES ({skill_exist[1]}, {skill_id}, {start_datetim}, {max_size}, '{note}')""")
                    new_class = do_database_fetchone(f"SELECT classid FROM class WHERE note = '{note}'")[0]
                    response.append(build_response_redirect(f"/class/{new_class}"))
                    # response.append(build_response_message(0, "Successfully created class"))
                except Exception as e:
                    print('skill',skill_exist[1])
                    response.append(build_response_message(242, f"Internal error : {str(e)}"))
    # response.append(build_response_message(301, "Bad parameter"))
    return [iuser, imagic, response]

# HTTPRequestHandler class
class myHTTPServer_RequestHandler(BaseHTTPRequestHandler):

    # POST This function responds to GET requests to the web server.
    def do_POST(self):

        # The set_cookies function adds/updates two cookies returned with a webpage.
        # These identify the user who is logged in. The first parameter identifies the user
        # and the second should be used to verify the login session.
        def set_cookies(x, user, magic):
            ucookie = Cookie.SimpleCookie()
            ucookie['u_cookie'] = user
            x.send_header("Set-Cookie", ucookie.output(header='', sep=''))
            mcookie = Cookie.SimpleCookie()
            mcookie['m_cookie'] = magic
            x.send_header("Set-Cookie", mcookie.output(header='', sep=''))

        # The get_cookies function returns the values of the user and magic cookies if they exist
        # it returns empty strings if they do not.
        def get_cookies(source):
            rcookies = Cookie.SimpleCookie(source.headers.get('Cookie'))
            user = ''
            magic = ''
            for keyc, valuec in rcookies.items():
                if keyc == 'u_cookie':
                    user = valuec.value
                if keyc == 'm_cookie':
                    magic = valuec.value
            return [user, magic]

        # Fetch the cookies that arrived with the GET request
        # The identify the user session.
        user_magic = get_cookies(self)

        print(user_magic)

        # Parse the GET request to identify the file requested and the parameters
        parsed_path = urllib.parse.urlparse(self.path)

        # Decided what to do based on the file requested.

        # The special file 'action' is not a real file, it indicates an action
        # we wish the server to execute.
        if parsed_path.path == '/action':
            self.send_response(200) #respond that this is a valid page request

            # extract the content from the POST request.
            # This are passed to the handlers.
            length =  int(self.headers.get('Content-Length'))
            scontent = self.rfile.read(length).decode('ascii')
            print(scontent)
            if length > 0 :
              content = json.loads(scontent)
            else:
              content = []

            # deal with get parameters
            parameters = urllib.parse.parse_qs(parsed_path.query)

            if 'command' in parameters:
                # check if one of the parameters was 'command'
                # If it is, identify which command and call the appropriate handler function.
                # You should not need to change this code.
                if parameters['command'][0] == 'login':
                    [user, magic, response] = handle_login_request(user_magic[0], user_magic[1], content)
                    #The result of a login attempt will be to set the cookies to identify the session.
                    set_cookies(self, user, magic)
                elif parameters['command'][0] == 'logout':
                    [user, magic, response] = handle_logout_request(user_magic[0], user_magic[1], parameters)
                    if user == '!': # Check if we've been tasked with discarding the cookies.
                        set_cookies(self, '', '')
                elif parameters['command'][0] == 'get_my_skills':
                    [user, magic, response] = handle_get_my_skills_request(user_magic[0], user_magic[1])
                    if user == '!': # Check if we've been tasked with discarding the cookies.
                        set_cookies(self, '', '')

                elif parameters['command'][0] == 'get_upcoming':
                    [user, magic, response] = handle_get_upcoming_request(user_magic[0], user_magic[1])
                    if user == '!': # Check if we've been tasked with discarding the cookies.
                        set_cookies(self, '', '')
                elif parameters['command'][0] == 'join_class':
                    [user, magic, response] = handle_join_class_request(user_magic[0], user_magic[1],content)
                    if user == '!': # Check if we've been tasked with discarding the cookies.
                        set_cookies(self, '', '')
                elif parameters['command'][0] == 'leave_class':
                    [user, magic, response] = handle_leave_class_request(user_magic[0], user_magic[1],content)
                    if user == '!': # Check if we've been tasked with discarding the cookies.
                        set_cookies(self, '', '')

                elif parameters['command'][0] == 'get_class':
                    [user, magic, response] = handle_get_class_detail_request(user_magic[0], user_magic[1],content)
                    if user == '!': # Check if we've been tasked with discarding the cookies.
                        set_cookies(self, '', '')

                elif parameters['command'][0] == 'update_attendee':
                    [user, magic, response] = handle_update_attendee_request(user_magic[0], user_magic[1],content)
                    if user == '!': # Check if we've been tasked with discarding the cookies.
                        set_cookies(self, '', '')

                elif parameters['command'][0] == 'cancel_class':
                    [user, magic, response] = handle_cancel_class_request(user_magic[0], user_magic[1],content)
                    if user == '!': # Check if we've been tasked with discarding the cookies.
                        set_cookies(self, '', '')

                elif parameters['command'][0] == 'create_class':
                    [user, magic, response] = handle_create_class_request(user_magic[0], user_magic[1],content)
                    if user == '!': # Check if we've been tasked with discarding the cookies.
                        set_cookies(self, '', '')
                else:
                    # The command was not recognised, report that to the user. This uses a special error code that is not part of the codes you will use.
                    response = []
                    response.append(build_response_message(901, 'Internal Error: Command not recognised.'))

            else:
                # There was no command present, report that to the user. This uses a special error code that is not part of the codes you will use.
                response = []
                response.append(build_response_message(902,'Internal Error: Command not found.'))

            text = json.dumps(response)
            print(text)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(bytes(text, 'utf-8'))

        else:
            # A file that does n't fit one of the patterns above was requested.
            self.send_response(404) # a file not found html response
            self.end_headers()
        return

   # GET This function responds to GET requests to the web server.
   # You should not need to change this function.
    def do_GET(self):

        # Parse the GET request to identify the file requested and the parameters
        parsed_path = urllib.parse.urlparse(self.path)

        # Decided what to do based on the file requested.

        # Return a CSS (Cascading Style Sheet) file.
        # These tell the web client how the page should appear.
        if self.path.startswith('/css'):
            self.send_response(200)
            self.send_header('Content-type', 'text/css')
            self.end_headers()
            with open('.'+self.path, 'rb') as file:
                self.wfile.write(file.read())

        # Return a Javascript file.
        # These contain code that the web client can execute.
        elif self.path.startswith('/js'):
            self.send_response(200)
            self.send_header('Content-type', 'text/js')
            self.end_headers()
            with open('.'+self.path, 'rb') as file:
                self.wfile.write(file.read())

        # A special case of '/' means return the index.html (homepage)
        # of a website
        elif parsed_path.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            with open('./pages/index.html', 'rb') as file:
                self.wfile.write(file.read())

        # Pages of the form /create/... will return the file create.html as content
        # The ... will be a class id
        elif parsed_path.path.startswith('/class/'):
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            with open('./pages/class.html', 'rb') as file:
                self.wfile.write(file.read())

        # Pages of the form /create/... will return the file create.html as content
        # The ... will be a skill id
        elif parsed_path.path.startswith('/create/'):
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            with open('./pages/create.html', 'rb') as file:
                self.wfile.write(file.read())

        # Return html pages.
        elif parsed_path.path.endswith('.html'):
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            with open('./pages'+parsed_path.path, 'rb') as file:
                self.wfile.write(file.read())
        else:
            # A file that does n't fit one of the patterns above was requested.
            self.send_response(404)
            self.end_headers()

        return

def run():
    """This is the entry point function to this code."""
    print('starting server...')
    ## You can add any extra start up code here
    # Server settings
    # When testing you should supply a command line argument in the 8081+ range

    # Changing code below this line may break the test environment. There is no good reason to do so.
    if(len(sys.argv)<2): # Check we were given both the script name and a port number
        print("Port argument not provided.")
        return
    server_address = ('127.0.0.1', int(sys.argv[1]))
    httpd = HTTPServer(server_address, myHTTPServer_RequestHandler)
    print('running server on port =',sys.argv[1],'...')
    httpd.serve_forever() # This function will not return till the server is aborted.

run()
