#Dylan Dang Lab 4
#Module 4: System, Threads, Processes


import tkinter as tk
from tkinter import messagebox
import tkinter.filedialog
import json
import requests
import urllib.request as ur
import os
import threading
import multiprocessing as mp
import time



class DisplayWin(tk.Toplevel) :
    def __init__(self, master, city) :
        super().__init__(master)

        #Set window color and title
        self.configure(bg="light gray")
        self.title("City Weather")

        #Create and display title
        self._titleLabel = tk.Label(self, text=f"Weather for {city.title()}", fg="blue", bg = "light gray")
        self._titleLabel.grid(row = 0, column = 2)


        #Create labels for each of the categories
        self._labelNames = ["Date", "High", "Low", "Wind", "UV"]
        for i in range(5) :
            self._label = tk.Label(self, text=self._labelNames[i], fg = "blue", bg = "light gray")
            self._label.grid(row = 1, column=i)

        
        #Display data for city 
        try :
            with open("weather_data.json", "r") as f :
                data = json.load(f)
                for ele in enumerate(data[city]) :
                    self._lb = tk.Listbox(self, bg="white", fg="black")
                    for i in data[city][ele[1]] :
                        self._lb.insert(tk.END, i)
                    self._lb.grid(row=2, column = ele[0])
        except (json.JSONDecodeError, FileNotFoundError) :
            print("File not found or is empty.")

def storeCoords(place) :
    '''
    Make API calls to store coords of cities in json file

    Parameters: 
    place : name of place/city

    Returns:
    Tuple of latitude and longitude of the city
    '''
    resp = requests.get(f"https://geocoding-api.open-meteo.com/v1/search?name={place}&count=10&language=en&format=json")
    
    #Loop through all locations of name, look for California
    for pl in resp.json()["results"]:
        if pl["admin1"] == "California" :
            return (pl["latitude"], pl["longitude"])




MPLOCK = mp.Lock()
def storeInput(place, q) :
    ''' use API calls get necessary info for city, add it to queue'''

    #Fetch data based on lat and long, write in json
    with MPLOCK :
        with open("coords.json", "r") as f:
            coords = json.load(f)
    
    resp2 = requests.get(f"https://api.open-meteo.com/v1/forecast?latitude={coords[place][0]}&longitude={coords[place][1]}&daily=temperature_2m_max,temperature_2m_min,wind_speed_10m_max,uv_index_max&temperature_unit=fahrenheit&wind_speed_unit=mph")


    #Ensure thread safe
    with MPLOCK :
        q.put((place, resp2.json()["daily"]))


class MainWin(tk.Tk) :
    def __init__(self) :
        super().__init__()

        #Initialize necessary containers
        self._placesDisplay = ["North Bay: Napa", 
                  "North Bay: Sonoma",
                  "The Coast: Santa Cruz",
                  "The Coast: Monterey",
                  "East Bay: Berkeley",
                  "East Bay: Livermore",
                  "Peninsula: San Francisco",
                  "Peninsula: San Mateo",
                  "South Bay: San Jose",
                  "South Bay: Los Gatos"]
        self._places = ["Napa", 
                        "Sonoma", 
                        "Santa Cruz", 
                        "Monterey", 
                        "Berkeley", 
                        "Livermore", 
                        "San Francisco",
                        "San Mateo",
                        "San Jose",
                        "Los Gatos"]
        self._clicked = set()
        self._coords = {}

        #Set background color
        self._bg = "light gray"
        self.configure(bg=self._bg)

        #Set title and create title and explanation label
        self.title("Travel Weather App")

        self._titleLabel = tk.Label(self, text="Look up weather at your destination", fg="Blue", bg = self._bg, font=("Arial", 25))
        self._titleLabel.grid(row=0, column=1,pady=5)

        self._explainLabel = tk.Label(self, text="Select destinations then click Submit", fg="blue", bg=self._bg)
        self._explainLabel.grid(row=1,column=1,pady=5)

        #Fetch data from api
        self._lock = mp.Lock()
        self.makeProcesses()

        #Create ListBox
        self._LB = tk.Listbox(self, selectmode=tk.MULTIPLE, bg="white", fg="black")
        for place in self._placesDisplay:
            self._LB.insert(tk.END, place)
        self._LB.grid(row=2,column=1)

        #Create submit button
        self._submitButton = tk.Button(self, text="Submit", fg="blue", bg=self._bg, command=self.submit)
        self._submitButton.grid(row=3,column=1,pady=2.5)
        

        #Set command if main window closed
        self.protocol("WM_DELETE_WINDOW", self.closingWindow)
    
    def makeProcesses(self) :
        '''Create processes to fetch latitude and longitude for each place'''

        pool = mp.Pool(processes=10)
        startTime = time.time()
        
        #Check if coords have already been stored
        if (not os.path.exists("coords.json") or os.path.getsize("coords.json") == 0) :
            
            #Pool processes
            coords = pool.map(storeCoords, self._places)
            
            #Store into dictionary
            for i in range(len(self._places)) :
                self._coords[self._places[i]] = coords[i]

            #Store into json
            with open("coords.json", "w") as f:
                json.dump(self._coords, f, indent=3)

            print(f"N5:{time.time() - startTime}")


    def submit(self) :
        '''When submit button is clicked, create process for each city call display windows accordingly'''

        pList = []
        self._startTime = time.time()
        q = mp.Queue()
        places = [self._LB.get(i).split(":")[1].strip() for i in self._LB.curselection()]
        
        #Clear listbox selections
        self._LB.selection_clear(0, tk.END)

        #Check if place is already stored in input file weather_data
        for place in places :
            self._clicked.add(place)

            #Make processes for API call
            t = mp.Process(target=storeInput, args=(place,q))
            pList.append(t)
            t.start()
            
        #Wait until all processes have finished running
        for p in pList :
            p.join()

        with open("weather_data.json", "r") as fr :

            #Load input file from before
            try:
                wData = json.load(fr)
            except:
                wData = {}
            
            #Insert new data
            for i in range(len(places)) :
                cur = q.get()
                if cur[0] not in wData:
                    wData.update({cur[0] : cur[1]})
        
        #Store into json
        with open("weather_data.json", "w") as fw :
            json.dump(wData, fw, indent=3)
            
        print(f"N6:{time.time() - self._startTime}")

        #Display each window
        for place in places: 
            DisplayWin(self, place)
        
    


    


    def closingWindow(self) :
        '''Ask user to save in directory of their selection'''

        #Destroy main window
        self.destroy()

        #Check to make sure user has selected and wants to save results
        if len(self._clicked) > 0 and messagebox.askyesno(title="Save", message="Save results in directory of your choice?") :

            #Display directory selection window
            self._chosenDir = tk.filedialog.askdirectory(initialdir='.', title="Select Directory")


            #If selected
            if self._chosenDir:

                os.system(f'touch {self._chosenDir}/weather.txt')
                #Create weather file
                file_path = os.path.join(self._chosenDir, "weather.txt")
                with open(f"{self._chosenDir}/weather.txt", "w") as f:

                    with open("weather_data.json", "r") as weather_data:
                        data = json.load(weather_data)
                        for place in self._clicked:
                            #Write place name
                            f.write(f"{place}:\n")

                            #Write data for place
                            for key in data[place]:
                                s = ", ".join(map(str, data[place][key]))
                                f.write(f'{s}\n')

                messagebox.showinfo(title="Save", message=f"File weather.txt has been saved in {self._chosenDir}")


if __name__ == "__main__" :
    app = MainWin()
    app.mainloop()



'''
                    serial     multithreading     multiprocessing
geocoding data      13.592        1.103              0.956
weather data        6.259         1.388              1.040

Serial is the slowest because it has to wait for one API request before it can move onto the next.
Both mutlithreading and multiprocessing are very close in time, but multiprocessing just takes the lead.
This is probably due to the GIL, which allows true parallel execution.

'''