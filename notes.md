### Future Improvements
- Principal reassignment



if authenticated
    if school registered
        if principal or admin
            go to: admin dashboard
        else if teacher
            if assigned to class
                go to: teacher dashboard
            else 
                msg: assign to class before accessing teacher dashboard
        else
            msg: assign a role to user
     else
        if principal
            go to: register school form
        else
            msg: assign user to a school
else
    go to: log in form

