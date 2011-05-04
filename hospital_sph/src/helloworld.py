from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
import urllib
import urllib2
import re
import datetime
import time

from django.utils import simplejson
from BeautifulSoup import BeautifulSoup          # For processing HTML
#import HTMLParser 

'''HTMLParser.attrfind = re.compile( 
r'\s*([a-zA-Z_][-.:a-zA-Z_0-9]*)(\s*=\s*' 
r'(\'[^\']*\'|"[^"]*"|[^\s>^\[\]{}\|\'\"]*))?')'''

def add_qoute( match ):
    value = '\"' + match.group()
    value = value[:-2] + '\">' + value[-1]
    return value

def make_message(status, message):
    m = {}
    m['status'] = status
    m['message'] = message
    return simplejson.dumps(m, sort_keys=True, ensure_ascii=False)

class FetchData():
    #initialization
    dept_data = []                              # used in /sph/dept
    doc_data = []                               # used in /sph/doctor
    dept_map = {}                               # map dept. name to dept. id
    doc_map = {}                                # map doctor name to doctor id
    doc_id_map = {}                             # map doctor id to doctor name
    dept_info = [[] for i in range(31)]         # used in /sph/dept?\xe8\x85\x8e\xe8\x87\x9f\xe7\xa7\x91id=N        
    doc_info = [[] for i in range(101)]         # used in /sph/doctor?id=N           
    doc_time = [[] for i in range(101)]         # store doctor available time 
    doc_dept = [[] for i in range(101)]         # store doctor available department
    doc_dept_set = [set() for i in range(101)]  # current set of departments of the doctor
    doc_time_set = [set() for i in range(101)]  # current set of available time of doctor
    
    register_info = {}                          # map tuple (date, doc_id, dept_id) to URL address
    dept_count = 1                              # count current index of department
    doc_count = 1                               # count current index of doctor
    dept_set = set()                            # current occurred department while searching
    doc_set = set()                             # current occurred doctor while searching
    
    delta = datetime.timedelta(hours = 8)
    utc = datetime.datetime.today()
    today = utc + delta
    date_today = datetime.date(today.year, today.month, today.day)
    
    sphUrl = "http://rms.sph.org.tw/sphrms/"
    page = urllib2.urlopen(sphUrl + "rms-sph.htm")
    soup = BeautifulSoup(page)
    target = soup.findAll('a', {'href' : re.compile('.*asp\?dpt.*')}, {'class': 'sub'})
    for iter in target:
        #initialization
        dept_time = []                          # store doctors in the department
        dept_doc = []                           # store dates in the department
        dept_time_set = set()                   # current occurred date in the department
        dept_doc_set = set()                    # current occurred doctor in the department
        if iter.span != None:
            dept_name = iter.span.string.strip()
        else:
            dept_name = iter.string.strip()
        if dept_name not in dept_set:
            dept = {}
            dept[dept_count] = dept_name
            dept_data.append(dept)
            dept_map[dept_name] = dept_count 
            dept_set.add(dept_name)
            dept_count += 1
        dept_id = dept_map[dept_name]
        nextUrl = sphUrl + iter['href']
        page = urllib2.urlopen(nextUrl)
        com = re.compile(r'\.\.\/rms_result.asp\?rmsdata=\S*>\d')
        page = com.sub(add_qoute, page.read())
        soup = BeautifulSoup(page)
        target_info = soup.findAll('a', {'href' : re.compile('.*asp\?rmsdata.*')})
        for iter_info in target_info:
            # get information of available time
            m = re.match('.*\?rmsdata=(\d{4})(\d{2})(\d{2})\d*NNNN(\w{2}).*', iter_info['href'])
            date_list = list(m.groups())
            avail_time = datetime.date(int(date_list[0]),int(date_list[1]),int(date_list[2]))
            
            if not (date_today <= avail_time and avail_time < date_today + datetime.timedelta(7)) :
                continue
            
            # get information of doctor
            doc_name = iter_info.string[5:]
            #doc_name = iter_info.string[5:].encode('UTF-8') will be wrong on GAE
            
            # handle information of doctor
            if doc_name not in doc_set:
                doc = {}
                doc[doc_count] = doc_name
                doc_id_map[doc_count] = doc_name
                doc_data.append(doc)
                doc_map[doc_name] = doc_count
                doc_set.add(doc_name)
                doc_count += 1
            doc_id = doc_map[doc_name]
            if doc_name not in dept_doc_set:
                doc = {}
                doc[doc_id] = doc_name 
                dept_doc.append(doc)
                dept_doc_set.add(doc_name)
            if dept_name not in doc_dept_set[doc_id]:
                dept = {}
                dept[dept_id] = dept_name
                doc_dept[doc_id].append(dept)
                doc_dept_set[doc_id].add(dept_name)
            # handle information of available time
            if date_list[3] == 'AM':
                date_list[3] = 'A'
            elif date_list[3] == 'PM':
                date_list[3] = 'B'
            elif date_list[3] == 'NT':
                date_list[3] = 'C'
            date = '-'.join(date_list)
            if date not in dept_time_set:             
                dept_time.append(date)
                dept_time_set.add(date)
            if date not in doc_time_set[doc_id]:
                doc_time[doc_id].append(date)
                doc_time_set[doc_id].add(date)
            register_info[(date, doc_id, dept_id)] = iter_info['href'].encode('big5')
            
        # create info for department of the current id
        id = {}
        name = {}
        doctor = {}
        time = {}
        # id = name = doctor = time = {} will be wrong, there will share same {}
        id['id'] = str(dept_id)
        name['name'] = dept_name
        dept_doc.sort()
        dept_time.sort()
        doctor['doctor'] = dept_doc
        time['time'] = dept_time
        dept_info[dept_id].append(id)
        dept_info[dept_id].append(name)
        dept_info[dept_id].append(doctor)
        dept_info[dept_id].append(time)
        # dept_info[dept_id].append(time).append(name) will be wrong
    # create info for doctor of all id
    for doc_id in range(1, doc_count):
        id = {}
        name = {}
        dept = {}
        time = {}
        id['id'] = str(doc_id)
        name['name'] = doc_id_map[doc_id]
        doc_dept[doc_id].sort()
        doc_time[doc_id].sort()
        dept['dept'] = doc_dept[doc_id]
        time['time'] = doc_time[doc_id]
        doc_info[doc_id].append(id)
        doc_info[doc_id].append(name)
        doc_info[doc_id].append(dept)
        doc_info[doc_id].append(time)    

class MainPage(webapp.RequestHandler):
    def get(self):
        self.response.out.write('HelloWorld!')

class Register(webapp.RequestHandler):
    def post(self):
        doctor = self.request.get('doctor')
        dept = self.request.get('dept')
        time = self.request.get('time').encode('big5')
        id = self.request.get('id')
        birthday = self.request.get('birthday')
        first = self.request.get('first')
        phone = self.request.get('phone')
        
        birth = birthday.split('-')
        if len(birth) == 3:
            birthday = birth[1] + birth[2] 
        
        if (time, int(doctor), int(dept)) not in FetchData.register_info:
            self.response.out.write(make_message('1', 'NotAvailableTime|Doctor|Department'))
            return
        
        m = re.match('.*\?rmsdata=(.*)&Dptname=(.*)', FetchData.register_info[(time, int(doctor), int(dept))])
        rmsdata = m.groups()[0] 
        dptcnm = m.groups()[1]
        
        if first == 'TRUE':
            if phone == '':
                self.response.out.write(make_message('2', dict(phone = '\xe9\x9b\xbb\xe8\xa9\xb1')))
                return 
            form_fields = {
                   'rmsdata': rmsdata,
                   'dptcnm': dptcnm,
                   'chtno' : '',
                   'birth' :'',
                   'phonenum': id,   #id
                   'comutel': phone, #phone number
                   'R1':'Y',
                   'submit':'\xb1\xbe\xb8\xb9' #submit
                   }
            form_data = urllib.urlencode(form_fields)           
            url = "http://rms.sph.org.tw/sphrms/rms_exec.asp"
            result = urllib.urlopen(url, form_data)
            result = result.read() 
            if re.search('.*deepskyblue.*', result, re.DOTALL) != None: # color of success word
                n = '0'
                num = re.match('.*>\s*(\d+)\s*<.*', result, re.DOTALL)
                if num != None:
                    n = num.groups()[0]
                self.response.out.write(make_message('0', n))
            else: # color of failed word is orange
                self.response.out.write(make_message('0', '-1'))
        elif first == 'FALSE': # NOT KNOWING ACTUAL SITUATION
            form_fields = {
                   'rmsdata': rmsdata,
                   'dptcnm': dptcnm,
                   'chtno' : id,
                   'birth' : birthday,
                   'phonenum': '',   #id
                   'comutel': '', #phone number
                   'R1':'Y',
                   'submit':'\xb1\xbe\xb8\xb9' #submit
                   }
            form_data = urllib.urlencode(form_fields)           
            url = "http://rms.sph.org.tw/sphrms/rms_exec.asp"  
            result = urllib.urlopen(url, form_data)
            self.response.out.write(make_message('0', '0')) # not handle register number
        
class CancelRegister(webapp.RequestHandler):
    def post(self):
        time = self.request.get('time').encode('big5')
        id = self.request.get('id')
        first = self.request.get('first')
        element = time.split('-')
        time = element[0] + element[1] + element[2] 
        if element[3] == 'A':
            time += 'AM'
        elif element[3] == 'B':
            time += 'PM'
        elif element[3] == 'C':
            time += 'NT'    
        
        if first == 'TRUE':
            # enter first page
            form_fields = {
                           'R1': 'V2',
                           'qchtno': id,
                           'submit': '\xacd\xb8\xdf'  #finding
                           }
            form_data = urllib.urlencode(form_fields)
            url = "http://rms.sph.org.tw/sphrms/rms_qresultl.asp"
            result = urllib.urlopen(url, form_data)
            # enter second page
            soup = BeautifulSoup(result)
            target = soup.findAll('input',{'id' : 'radio1', 'name' : 'cancelrgs'})
            if target == []:
                self.response.out.write(make_message('1', 'IDNotFound|SomeError'))
                return
            doSubmit = False
            for iter in target:
                m = re.match('(\w{10}).*', iter['value'])
                if m != None and m.groups()[0] == time:
                    form_fields = {
                                   'cancelrgs': iter['value'],
                                   'submit': '\xacd\xb8\xdf'
                                   }
                    form_data = urllib.urlencode(form_fields)   #finding
                    url = "http://rms.sph.org.tw/sphrms/rms_qresultl.asp" # same as above
                    result = urllib.urlopen(url, form_data)
                    doSubmit = True
                    break
            if doSubmit:
                m = {}
                m['status'] = '0'    
                self.response.out.write(simplejson.dumps(m, sort_keys=True, ensure_ascii=False))
            else:
                self.response.out.write(make_message('1', 'RequestDateNotFound'))
        else: # NOT KNOWING ACTUAL SITUATION
            # enter first page
            form_fields = {
                           'R1': 'V1',
                           'qchtno': id,
                           'submit': '\xacd\xb8\xdf'  #finding
                           }
            form_data = urllib.urlencode(form_fields)
            url = "http://rms.sph.org.tw/sphrms/rms_qresultl.asp"
            result = urllib.urlopen(url, form_data)
            # enter second page
            soup = BeautifulSoup(result)
            target = soup.findAll('input',{'id' : 'radio1', 'name' : 'cancelrgs'})
            if target == []:
                self.response.out.write(make_message('1', 'IDNotFound|SomeError'))
                return
            doSubmit = False
            for iter in target:
                m = re.match('(\w{10}).*', iter['value'])
                if m != None and m.groups()[0] == time:
                    form_fields = {
                                   'cancelrgs': iter['value'],
                                   'submit': '\xacd\xb8\xdf'
                                   }
                    form_data = urllib.urlencode(form_fields)   #finding
                    url = "http://rms.sph.org.tw/sphrms/rms_qresultl.asp" # same as above
                    result = urllib.urlopen(url, form_data)
                    doSubmit = True
                    break
            if doSubmit:
                m = {}
                m['status'] = '0'    
                self.response.out.write(simplejson.dumps(m, sort_keys=True, ensure_ascii=False))
            else:
                self.response.out.write(make_message('1', 'RequestDateNotFound'))
        
class Dept(webapp.RequestHandler):
    def get(self):
        id = self.request.get('id')
        if id != '':
            self.response.out.write(simplejson.dumps(FetchData.dept_info[int(id)], sort_keys=True, ensure_ascii=False))
        else:
            self.response.out.write(simplejson.dumps(FetchData.dept_data, sort_keys=True, ensure_ascii=False))
            

class Doctor(webapp.RequestHandler):
    def get(self):
        id = self.request.get('id')
        if id != '':
            self.response.out.write(simplejson.dumps(FetchData.doc_info[int(id)], sort_keys=True, ensure_ascii=False))
        else:
            self.response.out.write(simplejson.dumps(FetchData.doc_data, sort_keys=True, ensure_ascii=False))
 
class Form(webapp.RequestHandler):
    def get(self):
        self.response.out.write('''
        <html>
        <body>
        <h1>REGISTER</h1>
        <form method="post" action="/sph/register">
        DOCTOR <input type=text name=doctor></br>
        DEPARTMENT <input type=text name=dept></br>
        TIME(YYYY-MM-DD-A|B|C) <input type=text name=time></br>
        ID <input type=text name=id></br>
        PHONE <input type=text name=phone></br>
        <input type=radio name=first value=TRUE>FIRST
        <input type=radio name=first value=FALSE>NOT FIRST</br>
        <input type=submit value="SEND"><input type=reset value="RESET">
        </body>
        </html>''')
class CancelForm(webapp.RequestHandler):
    def get(self):
        self.response.out.write('''
        <html>
        <body>
        <h1>CANCEL REGISTER</h1>
        <form method="post" action="/sph/cancel_register">
        DOCTOR <input type=text name=doctor></br>
        DEPARTMENT <input type=text name=dept></br>
        TIME(YYYY-MM-DD-A|B|C) <input type=text name=time></br>
        ID <input type=text name=id></br>
        <input type=radio name=first value=TRUE>FIRST
        <input type=radio name=first value=FALSE>NOT FIRST</br>
        <input type=submit value="SEND"><input type=reset value="RESET">
        </body>
        </html>''')
         
application = webapp.WSGIApplication(
                                     [('/', MainPage),
                                      ('/sph/dept', Dept),
                                      ('/sph/doctor', Doctor),
                                      ('/sph/register', Register),
                                      ('/sph/form', Form),
                                      ('/sph/cancel_form', CancelForm),
                                      ('/sph/cancel_register', CancelRegister)],
                                     debug=True)

def main():
    run_wsgi_app(application)

if __name__ == "__main__":
    main()