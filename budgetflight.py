from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait 
from selenium.webdriver.support import expected_conditions
from bs4 import BeautifulSoup
import re
import pandas as pd
import numpy as np
from datetime import date, timedelta, datetime
import time

def scrape(origin, destination, startdate, days, requests):
    
    global results
    
    enddate = datetime.strptime(startdate, '%Y-%m-%d').date() + timedelta(days)
    enddate = enddate.strftime('%Y-%m-%d')

    url = "https://www.kayak.com/flights/" + origin + "-" + destination + "/" + startdate + "/" + enddate + "?sort=bestflight_a&fs=cfc=1;stops=0"
    print("\n" + url)

    chrome_options = webdriver.ChromeOptions()
    #Find your agent by searching "what is my user agent"
    agents = ["Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/78.0.3904.108 Safari/537.36"]
    print("User agent: " + agents[(requests % len(agents))])
    chrome_options.add_argument('--user-agent=' + agents[(requests % len(agents))] + '"')    
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    #Install chromedriver.exe
    driver = webdriver.Chrome(ChromeDriverManager().install())
    #Use the following command if you already have chromedriver.exe installed on your device and added to PATH
    #driver = webdriver.Chrome(executable_path="chromedriver.exe", options=chrome_options, desired_capabilities=chrome_options.to_capabilities())
    driver.implicitly_wait(20)
    driver.get(url)

    #Check if Kayak thinks that we're a bot
    time.sleep(5) 
    soup = BeautifulSoup(driver.page_source, 'lxml')
    if soup.find_all('p')[0].getText() == "Please confirm that you are a real KAYAK user.":
        print("Kayak thinks I'm a bot, so let's wait a bit and try again")
        driver.close()
        time.sleep(20)
        return "failure"

    time.sleep(20) #Wait 20 seconds for the page to load
    
    soup = BeautifulSoup(driver.page_source, 'lxml')
    
    #Get the departure and arrival times
    deptimes = soup.find_all('span', attrs={'class': 'depart-time base-time'})
    arrtimes = soup.find_all('span', attrs={'class': 'arrival-time base-time'})
    meridies = soup.find_all('span', attrs={'class': 'time-meridiem meridiem'})
    
    deptime = []
    for div in deptimes:
        deptime.append(div.getText()[:-1])    
        
    arrtime = []
    for div in arrtimes:
        arrtime.append(div.getText()[:-1])   

    meridiem = []
    for div in meridies:
        meridiem.append(div.getText())  
        
    deptime = np.asarray(deptime)
    deptime = deptime.reshape(int(len(deptime) / 2), 2)
    
    arrtime = np.asarray(arrtime)
    arrtime = arrtime.reshape(int(len(arrtime) / 2), 2)      
    
    meridiem = np.asarray(meridiem)
    meridiem = meridiem.reshape(int(len(meridiem) / 4), 4)
        
    #Get the flight's price
    regex = re.compile('Common-Booking-MultiBookProvider (.*)multi-row Theme-featured-large(.*)')
    price_list = soup.find_all('div', attrs={'class': regex})
    price = []
    for div in price_list:
        price.append(int(div.getText().split('\n')[3][1::1]))
        
    print("Fly to your destination from: " + str(price[0]) + " dollars.")

    df = pd.DataFrame({"origin" : origin,
                       "destination" : destination,
                       "startdate" : startdate,
                       "enddate" : enddate,
                       "price": price,
                       "currency": "USD",
                       "deptime_o": [m + str(n) for m,n in zip(deptime[:,0],meridiem[:,0])],
                       "arrtime_d": [m + str(n) for m,n in zip(arrtime[:,0],meridiem[:,1])],
                       "deptime_d": [m + str(n) for m,n in zip(deptime[:,1],meridiem[:,2])],
                       "arrtime_o": [m + str(n) for m,n in zip(arrtime[:,1],meridiem[:,3])]
                       })

    results = pd.concat([results, df], sort=False)
    driver.close() #Close the browser
    time.sleep(30) #Wait 30 seconds until the next request
    return "success"

#Create an empty dataframe
results = pd.DataFrame(columns=['origin','destination','startdate','enddate','deptime_o','arrtime_d','deptime_d','arrtime_o','currency','price'])
 
#Origin input section, as a unique 3-letter IATA code
origins = input("Enter your origin: ")

#Destinations input section, as a unique 3-letter IATA code
destinations = list()
numdest = input("Enter the number of preferable destinations: ")
for i in range(int(numdest)):
    dest = input("Enter your preferable destination: ")
    destinations.append(str(dest))
print(destinations)

#Start Dates input section, as YYYY-MM-DD
startdates = list()
numdate = input("Enter the number of preferable start dates: ")
for i in range(int(numdate)):
    date = input("Enter your preferable start dates: ")
    startdates.append(str(date))
print(startdates)

requests = 0
staydays = int(input("Enter the number of days you'll stay in your preferable destination: "))

for destination in destinations:
    for startdate in startdates:   
        requests = requests + 1
        while scrape(origins, destination, startdate, staydays, requests) != "success":
            requests = requests + 1
            
#Find the minimum price for each Destination-Start Date combination
results_agg = results.groupby(['destination','startdate'])['price'].min().reset_index().rename(columns={'min':'price'})       

#Visualize results using a heatmap
heatmap_results = pd.pivot_table(results_agg, values='price', index=['destination'], columns='startdate')
                     
import seaborn as sns
import matplotlib.pyplot as plt

sns.set(font_scale=1.5)
plt.figure(figsize = (14,6))
sns.heatmap(heatmap_results, annot=True, annot_kws={"size": 20}, fmt='.0f', cmap="RdYlGn_r")
plt.show()
