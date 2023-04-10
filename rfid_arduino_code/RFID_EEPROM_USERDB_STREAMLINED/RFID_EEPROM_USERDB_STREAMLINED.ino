
/*
* Open Source RFID Access Controller
*
* 4/3/2011 v1.32
* Last build test with Arduino v00.21
* Arclight - arclight@23.org
* Danozano - danozano@gmail.com
*
* Notice: This is free software and is probably buggy. Use it at
* at your own peril.  Use of this software may result in your
* doors being left open, your stuff going missing, or buggery by
* high seas pirates. No warranties are expressed on implied.
* You are warned.
*
* For latest downloads, including Eagle CAD files for the hardware, check out
* http://code.google.com/p/open-access-control/downloads/list
*
* Latest update moves strings to PROGMEM to free up memory and adds a
* console password feature.
*
*
* This program interfaces the Arduino to RFID, PIN pad and all
* other input devices using the Wiegand-26 Communications
* Protocol. It is recommended that the keypad inputs be
* opto-isolated in case a malicious user shorts out the
* input device.
* Outputs go to a Darlington relay driver array for door hardware/etc control.
* Analog inputs are used for alarm sensor monitoring.  These should be
* isolated as well, since many sensors use +12V. Note that resistors of
* different values can be used on each zone to detect shorting of the sensor
* or wiring.
*
* Version 1.00+ of the hardware implements these features and uses the following pin
* assignments on a standard Arduino Duemilanova or Uno:
*
* Relay outpus on digital pins 6,7,8,9
* DS1307 Real Time Clock (I2C):A4 (SDA), A5 (SCL)
* Analog pins (for alarm):A0,A1,A2,A3
* Reader 1: pins 2,3
* Reader 2: pins 4,5
* Ethernet: pins 10,11,12,13 (Not connected to the board, reserved for the Ethernet shield)
*
* Quickstart tips:
* Set the PASSWORD
* Define the static user list by swiping a tag and copying the value received into the #define values shown below
* Compile and upload the code, then log in via serial console at 57600,8,N,1
9/10/2012 SDC
Re-do of the EEPROM stuff, yo.
some notes:
considering string of FF's a blank
but you're not guaranteed a clear EEPROM yr first time out.
so you actually have to manually clear it B4 adding users
9/16/2012 SDC
x and y (delete/upsert) mostly work.
weird behavior w/ tag 'ffffff', tho!
suddenly can't add anything
(fixed, reset byteval)
note, restrict tag no to < ffffff (& 0xFFFFFF)
12/23/2012 SDC
Let's wrap shit up. Includes: one-shot command and auth. Really shitty (tag w/ pwd) at this point, but move to a hashing.
new add: append $password at end of your command to bypass restricted mode

1/16/2015 SDC

Add 'exit' sensor
Ensure pass lockout.
Used online pretty printer to fix the craptacular formatting: http://prettyprinter.de/index.php
maybe try this too http://codebeautify.org/

I also ripped out all the alarm shit.
We are not using it.

03/19/2023  Apple Muncy j.apple.muncy@gmail.com
Stripping out many parts to move to single reader and door control.

03/28/2023 Apple
Reads card.
Searches EEPROM
Manually adds new RFID to EEPROM
04/10/2023 Apple
Unwinding some functions to be simpler.

*/
//#include <Wire.h>         // Needed for I2C Connection to the DS1307 date/time chip
#include <EEPROM.h>       // Needed for saving to non-voilatile memory on the Arduino.
//#include <avr/pgmspace.h> // Allows data to be stored in FLASH instead of RAM



#include "EEPROM_UserDB.h"
//#include <DS1307.h>       // DS1307 RTC Clock/Date/Time chip library

// forked from github  paulo-raca/YetAnotherArduinoWiegandLibrary
#include <Wiegand.h>    // Wiegand 26 reader format libary

//#include <PCATTACH.h>     // Pcint.h implementation, allows for >2 software interupts.
/* Static user List - Implemented as an array for testing and access override
*/
long sdc  = 0xFFFFFF;                  // Name and badge number in HEX. We are not using checksums or site ID, just the whole
long dosman =  0xFFFFFF;                  // output string from the reader.
long apple = 0xFFFFFF;
const long  superUserList[] = {
	dosman,sdc,apple
}
;

bool DEBUG = true;
#define PIN_D0 2
#define PIN_D1 3
#define relayPin 4
                                                                                
                                                                                
                                                                                
// Super user table (cannot be changed by software)
#define DOORDELAY 5000                  // How long to open door lock once access is granted. (2500 = 2.5s)

#define DOORPIN relayPin       // Define the pin for electrified door 1 hardware


#define PRIV_TIMEOUT 600000 // you get a minute, then lockout
long privTimer = 0;


void receivedData(uint8_t* data, uint8_t bits, const char* message);
void receivedDataError(Wiegand::DataError error, uint8_t* rawData, uint8_t rawBits, const char* message);
void stateChanged(bool plugged, const char* message);
void pinStateChanged();
void readCommand();
void PROGMEMprintln(const char str[]);
void lockDoor();
void unlockDoor();
void logAccessGranted(long user, byte reader);
bool checkSuperuser(long input);
void logAccessDenied(long user, byte reader);



// Wiegand 
// These are the pins connected to the Wiegand D0 and D1 signals.
// Ensure your board supports external Interruptions on these pins




// Relay output pins
bool doorLocked = true;

unsigned long doorlocktimer=0;
// Keep track of when door is supposed to be relocked

unsigned long consolefailTimer=0;
// Console password timer for failed logins
byte consoleFail=0;
int numUsers = (sizeof(superUserList)/sizeof(long)) ;                 //User access array size (used in later loops/etc)
#define NUMDOORS (sizeof(doorPin)/sizeof(byte))
//#define numAlarmPins (sizeof(analogsensorPins)/sizeof(byte))
// going this way son
char* PASSWORD = "ffffffff";
//Other global variables
byte second, minute, hour, dayOfWeek, dayOfMonth, month, year;
// Global RTC clock variables. Can be set using DS1307.getDate function.
// long because we need 32 bits to hold 24 bit long RFID 
volatile long reader= 0;
volatile int  readerCount = 0;

int userMask=0;

// Serial terminal buffer (needs to be global)

// Serial terminal buffer (needs to be global)
char inString[40]={
	0
}
;
// Size of command buffer (<=128 for Arduino)
byte inCount=0;

boolean privmodeEnabled = false;
// Switch for enabling "priveleged" commands

/* Create an instance of the various C++ libraries we are using.
*/

Wiegand wiegand;


EEPROM_UserDB UserDB;
/* Set up some strings that will live in flash instead of memory. This saves our precious 2k of
* RAM for something else.
*/


void setup(){
	
  Serial.begin(9600);
	
  //Install listeners and initialize Wiegand reader
  wiegand.onReceive(receivedData, "Card reader: ");
  wiegand.onReceiveError(receivedDataError, "Card read error: ");
  wiegand.onStateChange(stateChanged, "State changed: ");
  wiegand.begin(Wiegand::LENGTH_ANY, true);

  //initialize pins as INPUT and attaches interruptions
  pinMode(PIN_D0, INPUT_PULLUP);
  pinMode(PIN_D1, INPUT_PULLUP);
  pinMode(DOORPIN, OUTPUT);

  attachInterrupt(digitalPinToInterrupt(PIN_D0), pinStateChanged, CHANGE);
  attachInterrupt(digitalPinToInterrupt(PIN_D1), pinStateChanged, CHANGE);

  //Sends the initial pin state to the Wiegand library
  pinStateChanged();
  logReboot();

}
void loop()                                     // Main branch, runs over and over again
{

  noInterrupts();
  wiegand.flush();
  interrupts();
  //Sleep a little -- this doesn't have to run very often.
  delay(100);

	readCommand();

	// Check for commands entered at serial console
	if (privmodeEnabled && ((millis() - privTimer) > PRIV_TIMEOUT)) {
		privmodeEnabled = false;
		Serial.println(F("Priveleged mode disabled."));
	}
	/* Check if doors are supposed to be locked and lock/unlock them
	* if needed. Uses global variables that can be set in other functions.
	*/
   
	if(((millis() - doorlocktimer) >= DOORDELAY) && (doorlocktimer !=0))
	{
		
			lockDoor();

	}
	
	/*  Set optional "failsafe" time to lock up every night.
	*/
       

	//	Serial.println(F("Door 1 locked for 2359 bed time."));
	
	// Notes: RFID polling is interrupt driven, just test for the reader1Count value to climb to the bit length of the key
	// change reader1Count & reader1 et. al. to arrays for loop handling of multiple reader output events
	// later change them for interrupt handling as well!
	// currently hardcoded for a single reader unit
	/* This code checks a reader with a 26-bit keycard input. Use the second routine for readers with keypads.
	* A 5-second window for commands is opened after each successful key access read.
	*/
	if(readerCount >= 24){
		//  When tag presented to reader1 (No keypad on this reader)
		//logTagPresent(reader1,1);
		//  write log entry to serial port
		/* Check a user's security level and take action as needed. The
		*  usermask is a variable from 0..255. By default, 0 and 255 are for
		*  locked out users or uninitialized records.
		*  Modify these for each door as needed.
		*/
		userMask = UserDB.checkUser(reader);
		if(userMask>=0) {
			switch(userMask) {
				case 0:                                      // No outside privs, do not log denied.
				{
					Serial.print(F("User "));
					Serial.print(userMask,DEC);
					Serial.println(F(" locked out."));

					break;
				}
				case 255:                                              // Locked out user
				{
					Serial.print(F("User "));
					Serial.print(userMask,DEC);
					Serial.println(F(" locked out."));
					break;
				}
				default:
				{
					logAccessGranted(reader, 1);
					// Log and unlock door 1
		
					unlockDoor();
					// Unlock the door.
					break;
				}
			}
		}

		else
		{
			if(checkSuperuser(reader)) {
				// Check if a superuser, grant access.
				logAccessGranted(reader, 1);
				// Log and unlock door 1
				unlockDoor();
				// Unlock the door.
			}
			else {
				logAccessDenied(reader,1);
			}
		}

	reader = 0;
    readerCount = 0;
		// Reset for next tag scan
	}
	




// End of loop()



}
/*

 Access System Functions - Modify these as needed for your application.
These function control lock/unlock and user lookup.
*/
bool checkSuperuser(long input){
	// Check to see if user is in the user list. If yes, return their index value.
	bool found= false;
	for(int i=0; i<numUsers; i++){
		if(input == superUserList[i]){
			Serial.print("Superuser ");
			Serial.print(i,DEC);
			Serial.println(" found.");
			found= true;
			return found;
		}
	}
	return found;
	//If no, return false
}

void unlockDoor() {
	//Send an unlock signal to the door and flash the Door LED
	int dp;
	dp=DOORPIN;
	
	Serial.print("doorpin is  ");
    Serial.println(dp, DEC);
  
	digitalWrite(dp, HIGH);
	Serial.println(F("Door unlocked"));
	doorLocked = false;
    doorlocktimer=millis();
}

void lockDoor() {
	//Send an lock signal to the door and flash the Door LED
	int dp;
	dp=DOORPIN;

	digitalWrite(dp, LOW);
	Serial.println(F("Door locked"));
	doorLocked = true;
	doorlocktimer=0;
}



void logReboot() {
	Serial.println(F("Access Control System rebooted."));
}

void logTagPresent (long user, byte reader) {
	Serial.print(F("User "));
	if(DEBUG){
		Serial.print(user,HEX);
	}
	Serial.print(F(" presented tag at reader "));
	Serial.println(reader,DEC);

}

void logAccessGranted(long user, byte reader) {
	//Log Access events
	Serial.print(F("User "));
	if(DEBUG){
		Serial.print(user,HEX);
	}
	Serial.print(F(" granted access at reader "));
	Serial.println(reader,DEC);
}

void logAccessDenied(long user, byte reader) {
	//Log Access denied events
	Serial.print(F("User "));
	if(DEBUG){
		Serial.print(user,HEX);
	}
	Serial.print(F(" denied access at reader "));
	Serial.println(reader,DEC);
}



void logunLock(long user, byte door) {
	Serial.print(F("User "));
	Serial.print(user,DEC);
	Serial.print(F(" unlocked door "));
	Serial.println(door,DEC);
}

void logprivFail() {
	Serial.println(F("Privilage mode not enabled."));
}

/* Displays a serial terminal menu system for
* user management and other tasks
*/
void readCommand() {
	boolean requestValidated = false;
	// valid for current request only
	byte stringSize=(sizeof(inString)/sizeof(char));
	char cmdString[4][9];
	// Size of commands (4=number of items to parse, 10 = max length of each)
	char password[10];
	// max (ieeee)
	byte j=0;
	// Counters
	byte k=0;
	char cmd=0;
	char ch;
	password[0] = 0;
	/*
	SDC remarks. Slightly hacky 'signing'
	command$password
	will check the password and kick off priv mode if good.
	gives the 'too bad' msg if not.
	*/
	if (Serial.available()) {
        
		// Check if user entered a command this round
		ch = Serial.read();
		if( ch == '\r' || inCount >=stringSize-1)  {
			// Check if this is the terminating carriage return
			inString[inCount] = 0;
			inCount=0;
                 
		}
		else{
			(inString[inCount++] = ch);
		}
		//Serial.print(ch);
		// Turns echo on or off
		if(inCount==0) {
			// done readin
			cmd = inString[0];
			for(byte i=0;
			i<stringSize && password[0] == 0;
			i++) {
				cmdString[j][k] = inString[i];
				if(k<9) k++;
				else break;
				if(inString[i] == ' ') // Check for space and if true, terminate string and move to next string.
				{
					cmdString[j][k-1]=0;
					if(j<3)j++;
					else break;
					k=0;
				}
				else if (inString[i] == '$') {
					// terminate and move on(?)
					cmdString[j][k-1]=0;
					// this 'backing up - not good son'
					j++;
					k=1;
					while(inString[i+k] != 'r') {
						password[k-1] = inString[i+k];
						if(k<10) k++;
						else break;
					}
					password[k] = 0;
					break;
				}
				// password is always last - note, try a more unified approach.
			}
			// password always seems to wipe cmd
			// cmd = cmdString[0][0];
			// weird. just assign cmd at the beginning. then all is ok. This is fucked
			if(password[0] != 0) {
				if((consoleFail>=5) && (millis()-consolefailTimer<300000))  // Do not allow priv mode if more than 5 failed logins in 5 minute
				{
					Serial.println(F("Too many failed attempts. Try again later."));
				}
				else if(strcmp(password,PASSWORD) == 0) {
					consoleFail=0;
					requestValidated = true;
				}
				else {
					Serial.println(F("Too many failed attempts. Try again later."));
					privmodeEnabled=false;
					if(consoleFail==0) {
						// Set the timeout for failed logins
						consolefailTimer=millis();
					}
					consoleFail++;
					// Increment the login failure counter
				}
			}
			
			// note - privmodeEnabled is a per request in this model.
  
     switch (cmd) {
				case 'e': {
					// Enable "privileged" commands at console
					if((consoleFail>=5) && (millis()-consolefailTimer<300000))  // Do not allow priv mode if more than 5 failed logins in 5 minute
					{
						// Serial.println(privsAttemptsMessage);
					}
					// compare the substring
					if (strcmp(cmdString[1],PASSWORD) == 0)
					{
						consoleFail=0;
						Serial.println(F("Priveleged mode enabled."));
						privmodeEnabled=true;
						privTimer = millis();
					}
					else {
						// Serial.println(F("Priveleged mode disabled."));
						privmodeEnabled=false;
						if(consoleFail==0) {
							// Set the timeout for failed logins
							consolefailTimer=millis();
						}
						consoleFail++;
						// Increment the login failure counter -- only drops if success!
					}
					break;
				}
				case 'a': {
					// List whole user database
					if(privmodeEnabled==true || requestValidated == true) {
						Serial.println("");
						Serial.print("UserNum:");
						Serial.print("t");
						Serial.print("Usermask:");
						Serial.print("t");
						Serial.println("TagNum:");
						UserDB.dumpUsers();
					}
					else{
						logprivFail();
					}
					break;
				}
				case 's': {
					// List user
					if(privmodeEnabled==true || requestValidated == true) {
						UserDB.getUserMask(strtoul(cmdString[1],NULL,16));
					}
					else{
						logprivFail();
					}
					break;
				}
			
				case 'u': {
					if(privmodeEnabled==true || requestValidated == true) {
						unlockDoor();
					}
					else{
						logprivFail();
					}
					break;
				}
				case 'l': {
					// Lock all doors
					lockDoor();
					//  chirpAlarm(1);
					break;
				}
				
				case '9': {
					// Show site status
					Serial.print(F( "Door is "));

					Serial.println(doorLocked ? "locked" : "unlocked");
					break;
				}
				case 'o': {
					if(privmodeEnabled==true || requestValidated == true) {
						unlockDoor();  // Open the door
						break;
						
					}
					else {
						logprivFail();
					}
					break;
				}
				case 'm': {
					// add or update
                    Serial.print("cmd string 2 ");
                    Serial.println( atoi(cmdString[2]), HEX);
					if(privmodeEnabled==true || requestValidated == true) {
						UserDB.upsertUser(atoi(cmdString[2]), strtoul(cmdString[1],NULL,16));
					}
					else {
						logprivFail();
					}
					break;
				}
				case 'z': {
					// 'zap' it
					if(privmodeEnabled==true || requestValidated == true) {
						UserDB.clearUsers();
					}
					else {
						logprivFail();
					}
					break;
				}
				case 'r': {
					if(privmodeEnabled==true || requestValidated == true) {
						UserDB.deleteUser(strtoul(cmdString[1],NULL,16));
					}
					else{
						logprivFail();
					}
					break;
				}
				case '?': {
					// Display help menu
					 Serial.println(F("Valid commands are:"));
					 Serial.println(F("(s)show user <tagNumber>, (m)odify user <tagnumber> <usermask>"));
					 Serial.println(F("(a)ll user dump, (r) remove user <tagnumber>, (o)open door <num>"));
					 Serial.println(F("(z)ap all users, (u)nlock doors,(l)lock doors"));
					 Serial.println(F("(9)show_status"));
					 Serial.println(F("(e)nable <password> - enable or disable priveleged mode"));
					break;
				}
				default:
				 Serial.println(F("Invalid command. Press '?' for help."));
				break;
			}
			// end switch
		}
		// End of 'if' for reading is done
	}
	// End of 'if' for serial reading.
}


// When any of the pins have changed, update the state of the wiegand library
void pinStateChanged() {
  wiegand.setPin0State(!digitalRead(PIN_D0));
  wiegand.setPin1State(!digitalRead(PIN_D1));
}

// Notifies when a reader has been connected or disconnected.
// Instead of a message, the seconds parameter can be anything you want -- Whatever you specify on `wiegand.onStateChange()`
void stateChanged(bool plugged, const char* message) {
    Serial.print(message);
    Serial.println(plugged ? "CONNECTED" : "DISCONNECTED");
}

// Notifies when a card was read.
// Instead of a message, the seconds parameter can be anything you want -- Whatever you specify on `wiegand.onReceive()`
void receivedData(uint8_t* data, uint8_t bits, const char* message) {
    reader = 0;
    readerCount = bits;    
//    Serial.println("From receivedData");
//    Serial.print(message);
//    Serial.print(bits);
//    Serial.print("bits / ");
    //Print value in HEX
    
    uint8_t bytes = (bits+7)/8;
    for (int i=0; i<bytes; i++) {
        reader = reader << 8;
        reader = reader | data[i];
//        Serial.print(data[i] >> 4, 16);
  //      Serial.print(data[i] & 0xF, 16);
    }
//    Serial.println();
//    Serial.println(reader);
//    Serial.println();
}

// Notifies when an invalid transmission is detected
void receivedDataError(Wiegand::DataError error, uint8_t* rawData, uint8_t rawBits, const char* message) {
    Serial.print(message);
    Serial.print(Wiegand::DataErrorStr(error));
    Serial.print(" - Raw data: ");
    Serial.print(rawBits);
    Serial.print("bits / ");

    //Print value in HEX
    uint8_t bytes = (rawBits+7)/8;
    for (int i=0; i<bytes; i++) {
        Serial.print(rawData[i] >> 4, 16);
        Serial.print(rawData[i] & 0xF, 16);
    }
    Serial.println();
}
