from datetime import datetime
from itertools import groupby
import json
import time
from urllib.request import urlopen

from bs4 import BeautifulSoup

from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent

def getTeamsLastXMeets(soup, numberOfMeets=2):
    latestResultsAnchorTags = soup.find('h3',string='LATEST RESULTS').find_parent().find_parent().find('tbody').find_all('a')
    lastXMeets = []
    for x in range(numberOfMeets):
        lastXMeets.append("https://www.tfrrs.org" + latestResultsAnchorTags[x]['href'])
    return lastXMeets

def getAthletesLastXMeets(soup, numberOfMeets=2):
    recentMeetsForAthlete = soup.find('div',id='meet-results').find_all('table')
    recentMeetURLs=[]
    recentMeets = []
    if(len(recentMeetsForAthlete)<numberOfMeets):
        numberOfMeets=len(recentMeetsForAthlete)
    for x in range(numberOfMeets):
        recentMeets.append(recentMeetsForAthlete[x])
        recentMeetURLs.append(recentMeetsForAthlete[x].find('thead').find('a')['href'])
    return recentMeetURLs,recentMeets

def getTeamsLinksAndNames(soup):
    teamLinks,teamNames=[],[]
    tableData=soup.find("h3", string="TEAMS").parent.find("table").find_all("a")
    for index,eachTeam in enumerate(tableData):
        if(index%2==0):
            teamLinks.append(eachTeam["href"])
            teamNames.append(eachTeam.text.replace('Wis.-',''))
    return teamLinks, teamNames

def getTeamsAthleteLinksAndNames(teamLinks):
    teamAthleteLinks, teamAthleteNames = [],[]
    for eachTeam in teamLinks:
        html = openHTTPUrl(eachTeam)
        soup=BeautifulSoup(html.read(), "html.parser")
        athleteLinks,athleteNames = getAthleteLinksAndNames(soup)
        teamAthleteLinks.append(athleteLinks)
        teamAthleteNames.append(athleteNames)
    return teamAthleteLinks, teamAthleteNames

def getAthleteLinksAndNames(soup):
    athleteLinksATag = soup.find('h3',string='ROSTER').find_parent().find('tbody').find_all('a')
    athleteNames,athleteLinks=[],[]
    for eachLink in athleteLinksATag:
        nameParts=eachLink.getText().split(', ')
        athleteNames.append(nameParts[1].strip()+' '+nameParts[0].strip())
        athleteLinks.append('https://www.tfrrs.org'+eachLink['href'])
    return(athleteLinks,athleteNames)

def getAllTeamsLast2WeeksPrsPutInJSONFormat(url):
    html = openHTTPUrl(url)
    soup=BeautifulSoup(html.read(), "html.parser")
    ##All the teams links, team names for the conference
    teamLinks,teamNames = getTeamsLinksAndNames(soup)
    ##all the male athlete links and male athlete names for each team in their own array
    teamMaleAthleteLinks, teamMaleAthleteNames = getTeamsAthleteLinksAndNames(teamLinks)
    womensLinks = []
    for each in teamLinks:
        womensLinks.append(each.replace('_m_','_f_'))
    ##all the female athlete links and female athlete names for each team in their own array
    teamFemaleAthleteLinks, teamFemaleAthleteNames = getTeamsAthleteLinksAndNames(womensLinks)
    teamAthleteLinks,teamAthleteNames=[],[]
    ##Here we are combing all the athelte link and athletes names for each team, per each team
    ##meaning for each team in the conference there will be a list of all female and male links and
    ##female and male names.
    for index,each in enumerate(teamMaleAthleteLinks):
        teamAthleteLinks.append(each+teamFemaleAthleteLinks[index])
        teamAthleteNames.append(teamMaleAthleteNames[index]+teamFemaleAthleteNames[index])
    ##This will now process each team and all its athletes
    ##teamLinks, teamAthleteLinks, teamAthleteNames are parallel lists
    for teamIndex, eachTeamLink in enumerate(teamLinks):
        html = openHTTPUrl(eachTeamLink)
        soup=BeautifulSoup(html.read(), "html.parser")
        lastXMeets = getTeamsLastXMeets(soup)
        initalDictionary = []
        print(f"Current team is {teamNames[teamIndex]} {teamIndex + 1}/{len(teamNames)}")
        for athleteIndex,eachAthleteLink in enumerate(teamAthleteLinks[teamIndex]):
            #get their meet reuslt and check if pr recent
            percent = (athleteIndex + 1) / len(teamAthleteLinks[teamIndex]) * 100
            print(f"Progress: {percent:.2f}%", end="\r")
            html=openHTTPUrl(eachAthleteLink)
            soup=BeautifulSoup(html.read(), "html.parser")
            athleteRecentMeetURLs, athletesRecentMeets= getAthletesLastXMeets(soup)
            ##**COMPARE THE MEETS IF IT IS A SCHOOLS MOST RECENT CHECK FOR PRS IF NOT SKIP**##
            for meetIndex,eachMeet in enumerate(athleteRecentMeetURLs):
                if (eachMeet in lastXMeets):
                    inputDate = athletesRecentMeets[meetIndex].find('span').text.strip()
                    #Special case for dates like April 13-14, 2021
                    if '-' in inputDate:
                        split = inputDate.split('-')
                        split2 = split[1].split(',')
                        inputDate = split[0] +','+split2[1]
                    format="%b %d, %Y"
                    meetDate = datetime.strptime(inputDate,format).date()
                    meetName = athletesRecentMeets[meetIndex].find('thead').find('a').text.strip()
                    allPRsAtPRMeet = athletesRecentMeets[meetIndex].find_all('tr', class_='highlight')
                    for eachPRatPRMeet in allPRsAtPRMeet:
                        eventName = eachPRatPRMeet.find('td').text.strip()
                        pr = eachPRatPRMeet.find('a').text.strip()
                        initalDictionary.append((teamAthleteNames[teamIndex][athleteIndex],meetName,eventName,pr,meetDate))
        prepForJSON=[]
        sortedDictByDate = {k: list(g) for k, g in groupby(sorted(initalDictionary, key=lambda x: x[4], reverse=True), key=lambda x: x[4])}
        for eachDate,meetsAtDate in sortedDictByDate.items():
            sortedByMeet = {k: list(g) for k, g in groupby(sorted(meetsAtDate, key=lambda x: x[1]), key=lambda x: x[1])}
            for eachMeet,prs in sortedByMeet.items():
                listOfPRS = []
                uniqueNames=[]
                uniqueNameCount=0
                for eachPR in prs:
                    if (eachPR[0] not in uniqueNames):
                        uniqueNames.append(eachPR[0])
                        uniqueNameCount+=1;
                    listOfPRS.append({"athletename":eachPR[0],"eventname":eachPR[2],"pr":eachPR[3]})
                jsonMeetOBJ = {"meetname":eachMeet,
                            "meetdate":prs[0][4].strftime(format),
                            "numberofprs":len(prs),
                            "uniqueprs":uniqueNameCount,
                            "prsatmeet":listOfPRS}
                prepForJSON.append(jsonMeetOBJ)
        fileName = BASE_DIR / f'{teamNames[teamIndex].lower().replace(" ","-")}_recentrPRs.json'
        f = open(fileName, "w")
        f.write(json.dumps(prepForJSON, indent=4))
        f.close()

def openHTTPUrl(url):
    lastError = None
    for attempt in range(5):
        try:
            html = urlopen(url)
        except Exception as e:
            lastError = e
            if attempt < 4:  # Don't wait after the last attempt
                waitTime = 10 * (2 ** attempt)  # 10, 20, 40, 80 seconds
                print("Waiting "+str(waitTime)+" seconds")
                time.sleep(waitTime)
            continue
        else:
            return html
    print ("Issue opening url " + url)
    print(lastError)
    sys.exit(1)

print("Starting scraper...")
wiacTfrrsURL="https://www.tfrrs.org/leagues/1420.html"
americanRiversTfrrsURL="https://www.tfrrs.org/leagues/1400.html"
getAllTeamsLast2WeeksPrsPutInJSONFormat(wiacTfrrsURL)
getAllTeamsLast2WeeksPrsPutInJSONFormat(americanRiversTfrrsURL)

