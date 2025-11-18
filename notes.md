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

### To do list

[x] logo upload
[ ] favicon upload
[x] test script not showing test scores on reports
[x] formating of reports in bulk download
    [x] stars not being generated
    [x] footer placed too high
    [x] add school address and contact info
    [ ] possibly a "sticker" for outstanding students
    [x] increase font of data on report sheets
[x] review columns listed on finalize page
[x] disable edit and delete actions for tests that have been finalized
[x] once a term review has been finalized, disable the ability to create new tests in that term
[x] fix password change logic
[x] log out user when browser tab is closed
[ ] add show/hide password on login form
[x] incorporate `recommend_for_advancement` in term review
[x] add 'School reopens' in term review
[x] all students ordered by last name ascending
[x] order tests by date ascending
[x] come up with a name and domain
[ ] decide on what activities I want to capture and log
[ ] create an activity model and activity history table view
[ ] Populate recent activity box on dashboard
[x] allow the creation of multiple standard groups
[x] principals/admin cannot edit term reports
[x] Teachers should not edit or enroll students from student detail view
[x] Populate Student detail Academic Performance card with reports
[ ] work on transition sequence
[ ] clean up code that is no longer in use
[ ] work on optimizing queries that are duplicated
[ ] Write unit tests for the functionality as it is now
[ ] "Preferences" link for users to customize their experience (fixed header, dark mode, etc.)

### Documentation list

- Create a principal user account
- Principal sets up school info. this generates standards
- Principal sets year and term limits and number of school days
- Principal adds teachers and admin staff
- Principal/admin adds students, assigns to classes
- Principal/admin assigns teachers to classes
- Teacher adds subjects *
- Teacher creates tests
- Teacher adds scores
- Teacher completes and finalizes reports
- Teacher/principal/admin downloads reports


### Transition sequence

- Ensure new year and terms set up
- All students unenrolled at end of year
- students with `recommend_for_advancement` = True are advanced to next class
- students with `recommend_for_advancement` = False are repeated in same class
- STD 5 students graduate out of the system and set as inactive
- New students enrolled in Inf 1
- Teachers re-assigned to classes

### Things to understand
- dev vs prod workflow
- pdf generation 
- finalize flag for entire class
- possible refactor of long views.py files

### Marketing for the launch
- [ ] Optimize and redesign landing page
- [ ] Create a demo video
- [ ] Create a press release (contact Angelo)
- [ ] Create a social media campaign
- [ ] Set up a skool.com forum for teachers to discuss and request features and bug fixes
- [ ] Create a contact page
- [ ] Create a about page
