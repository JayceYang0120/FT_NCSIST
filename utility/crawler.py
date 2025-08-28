import re
import urllib.parse
import requests

from bs4 import BeautifulSoup

def get_html(jid: str) -> str:
    URL_JUDICIAL = "https://judgment.judicial.gov.tw/FJUD/data.aspx?ty=JD&id=" 
    url_JID = urllib.parse.quote(jid)
    url = URL_JUDICIAL + url_JID
    response = requests.get(url)
    if response.status_code == 200:
        return response.text
    else:
        print(f"Failed to retrieve data for {jid}. Status code: {response.status_code}")
        return None

def get_query(raw_html: str, pattern: str) -> tuple:
    """
    pattern_JudHistory = ../controls/GetJudHistory.ashx?jid=.*
    pattern_JudRelatedLaw = ../controls/GetJudRelatedLaw.ashx?pkid=.*

    args:
        -raw_html: string, raw HTML content of the page.
        -pattern: string, regex pattern to match the query string.
    returns:
        -return: tuple, (matched query string, response text) if found, else (None, None).
    """
    soup = BeautifulSoup(raw_html, "html.parser")
    scripts = soup.find_all("script")

    matches = []
    for script in scripts:
        if script.string:
            found = re.findall(pattern, script.string)
            matches.extend(found)
    if len(matches) == 1:
        match = matches[0]
        # remove the " in the beginning and end
        match = match.strip('"')
        url_query = match.replace("../", "https://judgment.judicial.gov.tw/")
        response_query = requests.get(url_query)
        if response_query.status_code == 200:
            return (match, response_query.text)
        else:
            print(
                f"Failed to retrieve JudHistory. Status code: {response_query.status_code}"
            )
            return (match, None)
    else:
        return (None, None)

def get_content(soup: BeautifulSoup, class_name: str) -> str:
    """
    Extracts content from the HTML based on the class name.
    args:
        -soup: BeautifulSoup object, parsed HTML content.
        -class_name: str, class name to search for.
    returns:
        -content: str, extracted content or empty string if not found.
    """
    if class_name == "text-pre text-pre-in":
        divs = soup.find_all("div", class_ = class_name)
        for div in divs:
            parent_td = div.find_parent("td")
            if parent_td and "tab_content" in parent_td.get("class", []):
                text = div.get_text(strip = True)
                return text
    else:
        div = soup.find("div", class_ = class_name)
        if div:
            text = div.get_text(separator = "\n", strip = True)
            return text
    return "-1"

def get_head(soup: BeautifulSoup, class_name_first: str, class_name_next: str, pattern: str) -> str:
    """
    Extracts the head of text from the HTML based on the class name.
    args:
        -soup: BeautifulSoup object, parsed HTML content.
        -class_name_first: str, class name for the first div.
        -class_name_next: str, class name for the next div.
        -pattern: str, regex pattern to match the title.
    returns:
        -head: str, extracted head or empty string if not found.
    """
    divs = soup.find_all("div", class_ = class_name_first)
    for label in divs:
        text = label.get_text(strip = True)
        if re.search(pattern, text):
            td = label.find_next_sibling("div", class_ = class_name_next)
            return td.get_text(strip = True) if td else ""
    return ""