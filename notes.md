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

### Security
Principals can request to whitelist a teacher's laptop/IP address
Or have the teachers install a VPN client to access the school's network

### Transitioning
In end of year report, indicate if student will advance or repeat 
should_repeat (default=False)

#### 0. Ensure the next academic year is set up

#### 1. Unassign all teachers (automatically unassigns classes)

#### 2. Graduate students sequentially
Create Transition section that only appears in Summer vacation between years
When transitioning from year to year
- unassign all teachers from classes
- class advance sequence:
    - graduate std 5 where should_repeat=False

Transition list view
- list of students, report summary, checked as Advance if should_repeat is False
- Confirm button to advance students to next class
- start from std 5, all unenrolled from class, all set to is_active=False
- Redirect to list view, std 5 complete, std 4 ready to advance

#### 3. Register new inf 1 students

#### 4. Assign teachers to classes

add filter for staff view

Overall average calculation detail?

## Functionality for MVP demo

bugs to fix

[ ] logo upload
[ ] favicon upload
[ ] test script not showing test scores on reports
[ ] formating of reports in bulk download
    [ ] stars not being generated
    [ ] footer placed too high
[ ] review columns listed on finalize page
[ ] fix password change logic
[ ] incorporate recommend to next level in term review
[ ] work on transition sequence
[ ] clean up code that is no longer in use

Set up a skool.com forum for teachers to discuss and request features and bug fixes
Come up with a name and domain
Create demno video

Documentation:
- Create a principal user account
- Principal sets up school info
- Principal sets year and term limits and number of school days
- Principal adds teachers and admin staff
- Principal/admin adds students, assignes to classes
- Principal/admin assigns teachers to classes
- Teacher adds subjects
- Teacher creates tests
- Teacher adds scores
- Teacher finalizes reports
- Teacher/principal/admin downloads reports


Teacher requests features and bug fixes