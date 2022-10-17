#############
# Basic function for plotting DWA json files
#
# Asks for file path and
# explicit first directory (based on 1c20db80-13aa-fc5a-6806-173f6332478d.json structure)
#
#
#
###
# John Waiton
# john.waiton@postgrad.manchester.ac.uk
############


### IMPROVEMENTS
# Set it up so that first directory generates new directory to insert files in, rather than overwriting previous files


import json
import pandas as pd
import matplotlib.pyplot as plt
import math as m
import os
import sys

#############
# loader
#############

def load_json(file_name):
    # Collects json data from file path

    # open file
    f = open(str(file_name))

    # return as dictionary
    data = json.load(f)

    # close json file
    f.close()

    return data


#################
# data scraper
#################


def data_scraper(data, init_dir):

    # Takes initial directory from user and (if path is correct, hard coded) will scrape all relevant data.

    selection = init_dir

    dict = {}

    # # digs through G, V, X, A, etc, Choose your starting environment
    for i in data[selection]:

        # (re)create the arrays
        wire_tension = []
        wire_tenstd = []
        wire_number = []
        # G - A, G - B, etc
        #print(i)
        for j in data[selection][str(i)]:
            # (re)create the arrays
            wire_tension = []
            wire_tenstd = []
            wire_number = []
            # each individual wire is here
            for k in data[selection][str(i)][str(j)]:

                # write wire number to array, then get the tension value for said wire
                wire_number.append(k)
                #print(k)

                # collect tension dictionary
                tens_dict = data[selection][str(i)][str(j)][str(k)]["tension"]

                # if no tension value (empty dictionary)
                if len(tens_dict) == 0:

                    wire_tension.append(0.0)
                    wire_tenstd.append(0.0)
                    #print('lol')
                else:
                    # if tension value exists, find it within dictionary. it'll be either 'tension': 'Not Found' or tension and tension_confidence
                    values = list(tens_dict.values())

                    # if statement 'Tension not found' occurs, don't collect tension_confidence or tension itself, just set to zero
                    if values[0]['tension'] == 'Not Found':
                                 wire_tension.append(0.0)
                                 wire_tenstd.append(0.0)
                    else:

                        wire_tension.append(values[0]['tension'])
                        wire_tenstd.append(values[0]['tension_confidence'])



            # now here, cleaning up the data basically, although not much
            namewt = 'wt'
            namewstd = 'wstd'
            namewno = 'wno'

            depth = str(i) + "_" + str(j)

            dict[depth] = {}
            dict[depth][namewt] = wire_tension
            dict[depth][namewstd] = wire_tenstd
            dict[depth][namewno] = wire_number

            # resetting to make sure it doesn't get messy
            del(wire_tension)
            del(wire_tenstd)
            del(wire_number)

    # return the dictionary
    return dict

##########
# plotter
##########

def plot_wires(dictionary ,A_B):
    # plots the given 'A_B' wire plane
    # now to plot this with a function

    plt.scatter(dictionary[str(A_B)]['wno'], dictionary[str(A_B)]['wt'], s = 10)
    plt.errorbar(dictionary[str(A_B)]['wno'], dictionary[str(A_B)]['wt'], yerr = dictionary[str(A_B)]['wstd'], fmt = 'none')
    # fill between given values for tolerance
    plt.fill_between(dictionary[str(A_B)]['wno'], 5.5, 7.5, color = 'purple', alpha = 0.3)

    # limit range
    plt.xlim([0,dictionary[str(A_B)]['wno'][-1:]])

    # remove a bunch of the ticks, currently every 100
    ticks = list(dictionary[str(A_B)]['wno'])
    plt.xticks([ticks[i] for i in range(len(ticks)) if i % 100 == 0], rotation='vertical')

    # labels
    plt.xlabel("Wire Number")
    plt.ylabel("Wire Tension (N)")

    # code this more complexly
    plt.title(str(A_B))

    #plt.show()


## main path
def main(path, first_key = ""):

    # collect data
    data = load_json(str(path))

    # print available dictionaries to probe (installation ones currently work, others im not so sure)
    print("Probe-able Dictionaries:")
    print(data.keys())
    print("")

    # if first_key is empty, ask user for key value that you will use
    if (first_key == ""):
        first_key = input("Enter name of relevant dictionary: ")

    # Scrape data
    print("Probing: {}...".format(str(first_key)))
    dicto = data_scraper(data, first_key)

    # ensure correct directories exist before plotting
    i_path = str("plots/individual")
    path = str("plots")
    #if not (os.path.exists(i_path)):
    #    if not (os.path.exists(path)):
    #
    #        os.makedirs(path)
    #
    #    os.makedirs(i_path)


    # plot data
    # print over each key
    for i in range(len(dicto.keys())):
        plot_wires(dicto, list(dicto.keys())[i])

        # save then close
        plt.savefig(i_path + "/" + str(list(dicto.keys())[i]))
        # close the plot
        plt.close()



        # Compiled image

    # for plotting, needs to be even number here
    plot_square = (round(m.sqrt(len(dicto.keys()))))

    # plotting function
    fig = plt.figure(figsize=(40,30))

    for index, image in enumerate(list(dicto.keys())):

        plt.subplot(plot_square, plot_square ,index+1)
        # plot image
        plot_wires(dicto, list(dicto.keys())[index])

    plt.savefig("plots/" + "compiled plots.png")
    plt.show()



# ensuring correct number of arguments
if len(sys.argv) == 3:
    main(sys.argv[1], sys.argv[2])
# if only one argument, ask user for first_key argument after displaying keys
elif len(sys.argv) == 2:
    main(sys.argv[1], "")
else:
    print("dwa_plot.py takes 1 or 2 arguments (" + str(len(sys.argv)-1) + ") given")
