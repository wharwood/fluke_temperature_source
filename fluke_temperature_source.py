from serial import Serial, SerialException
from time import sleep
import regex as re
            
class fluke_base:

    allowed_duplex_modes = ["half", "full"]
    allowed_temperature_units = ["f", "c"]
    __encoding_format = 'ascii'
    __duplex_mode = "half"
    __temperature_unit = "c"

    def __init__(self, port: str, baud: int = 2400, duplex: str = "half") -> None:
        """
        Initializes a connection to the Fluke 9141 temperature source over an RS-232 serial connection.

        Args:
            port: The serial port to connect to (e.g. 'COM3').
            baud: The baud rate for the serial connection (default is 2400). Warning: baud rates higher than 2400 may cause communication errors.
            duplex: The duplex mode for the serial connection, either 'half' or 'full' (default is 'half').

        Returns:
            None.
        """
        self.port = port
        self.baud = baud
        self.open()
        self.__duplex_mode = self.set_duplex_mode(duplex.lower())
        self.__temperature_unit = self.get_unit()

    def open(self) -> None:
        """
        Opens a serial connection to the Fluke 9141 temperature source.

        Args:
            None.

        Returns:
            None.
        """
        try:
            self.connection = Serial(port=self.port, baudrate=self.baud, timeout=1)
        except SerialException as e:
            raise e
        if not self.connection.is_open:
            raise ConnectionError(f'Failed to open connection on port {self.port} at {self.baud} baud.')

    def close(self) -> None:
        if self.connection.is_open:
            self.connection.close()

    def write(self, command: str, value: str|None = None) -> None:
        if value == None:
            input_string = f'{command}' + chr(13) + chr(10)
        else:
            input_string = f'{command}={value}' + chr(13) + chr(10)
        try:
            echo = self.connection.write(input_string.encode(self.__encoding_format))
        except SerialException as e:
            raise e
        if self.__duplex_mode == "full":
            if echo == None:
                raise ValueError('Device is in full duplex mode and no echo received.')
            echo = self.connection.read_until(chr(13).encode(self.__encoding_format)).decode(encoding=self.__encoding_format).strip()
            if command not in echo:
                raise ValueError(f'Command echo mismatch. Sent {command}, received {echo}.')

    def read(self, command: str) -> str:
        self.write(command)
        try:
            output = self.connection.readline()
        except SerialException as e:
            raise e
        if output == None:
            raise ValueError('No data received from device.')
        return output.decode(encoding=self.__encoding_format).strip()

    def set_duplex_mode(self, duplex: str) -> None:
            """
            Sets the duplex mode on the currently open connection.
            
            Args:
                duplex: The duplex mode 'half' or 'full'.

            Returns:
                None.
            """
            if duplex not in self.allowed_duplex_modes:
                raise ValueError(f'Duplex mode must be {', '.join(self.allowed_duplex_modes)}.')
            self.write('du', duplex)

    def get_temperature(self) -> float:
        """
        Reads the temperature of the block using the internal reference thermometer from currently open connection.

        Args:
            None.

        Returns:
            temp: A floating point representation of the temperature in the initialized temperature unit.
        """
        output = self.read('t')
        if output == None:
            raise ValueError('Failed to receive data.')
        match = re.match(r"t:\s+(\d+.\d+)\s+([CF])", output)
        if match == None:
            raise ValueError(f'Unexpected temperature format received: {output}.')
        temperature = match.group(1)
        unit = match.group(2)
        if unit.lower() != self.__temperature_unit.lower():
            raise ValueError(f'Temperature unit mismatch. Expected {self.__temperature_unit}, received {unit}. Please restart the temperature source')
        return float(temperature)

    def get_setpoint(self) -> float:
        """
        Reads the current temperature setpoint from currently open connection.

        Args:
            None.

        Returns:
            setpoint: A floating point representation of the set point in initialized temperature unit.
        """
        output = self.read('s')
        if output == None:
            raise ValueError('Failed to receive data.')
        match = re.match(r"set:\s+(\d+.\d+)\s+([CF])", output)
        if match == None:
            raise ValueError(f'Unexpected set point format received: {output}.')
        setpoint = match.group(1)
        unit = match.group(2)
        if unit.lower() != self.__temperature_unit.lower():
            raise ValueError(f'Setpoint unit mismatch. Expected {self.__temperature_unit}, received {unit}. Please restart the temperature source')
        return float(setpoint)
        
    def set_setpoint(self, value: float) -> None:
        """
        Sets the tempurature set point from currently open connection.

        Args:
            value: The temperature to set in the initialized unit.

        Returns:
            None.
        """
        if type(value) not in [int, float]:
            raise ValueError('Set point must be a number.')
        self.write('s', str(value))
    
    def get_unit(self) -> str:
        """
        Reads the current system temperature unit from currently open connection.

        Args:
            None.

        Returns:
            temperature_unit: A string with the current time and initialized temperature unit.
        """
        output = self.read('u')
        if output == None:
            raise ValueError('Failed to receive data.')
        match = re.match(r"u:\s+([CF])", output)
        if match == None:
            raise ValueError(f'Unexpected temperature unit format received: {output}.')
        temperature_unit = match.group(1).lower()
        return temperature_unit

    def set_unit(self, unit: str) -> None:
        """
        Sets the tempurature unit.

        Args:
            unit: A temperature unit 'c' for Celsius or 'f' for Fahrenheit.

        Returns:
            None.
        """
        if unit.lower() not in self.allowed_temperature_units:
            raise ValueError(f'Temperature unit {unit} not supported. Must be {", ".join(self.allowed_temperature_units)}.')
        self.write('u', unit)
        if self.get_unit().lower() == unit.lower():
            self.__temperature_unit = unit.lower()

    def get_proportional_band(self) -> float:
        """
        Reads the current proportional band from currently open connection.

        Args:
            None.

        Returns:
            proportional_band: A floating point representation of the proportional band in percent.
        """
        output = self.read('pr')
        if output == None:
            raise ValueError('Failed to receive data.')
        match = re.match(r"pr:\s+(\d+.\d+)", output)
        if match == None:
            raise ValueError(f'Unexpected proportional band format received: {output}.')
        proportional_band = float(match.group(1))
        return proportional_band
    
    def set_proportional_band(self, band: float) -> None:
        """
        Sets the proportional band on the currently open connection.

        Args:
            band: The proportional band in percent.

        Returns:
            None.
        """
        if type(band) not in [int, float]:
            raise ValueError('Proportional band must be a number.')
        if band < 0 or band > 100:
            raise ValueError('Proportional band must be between 0 and 100 percent.')
        self.write('pr', str(band))

    def get_heater_power(self) -> float:
        """
        Reads the current heater duty cycle from currently open connection.

        Args:
            None.

        Returns:
            heater_power: A floating point representation of the heater duty cycle in percent.
        """
        output = self.read('po')
        if output == None:
            raise ValueError('Failed to receive data.')
        match = re.match(r"po:\s+(\d+.\d+)", output)
        if match == None:
            raise ValueError(f'Unexpected heater power format received: {output}.')
        heater_power = float(match.group(1))
        return heater_power

    def get_firmware_version(self) -> str:
        """
        Reads the current firmware version from currently open connection.

        Args:
            None.

        Returns:
            firmware_version: A string with the current firmware version.
        """
        output = self.read('*ver')
        if output == None:
            raise ValueError('Failed to receive data.')
        match = re.match(r"ver.(d+),\s*(d+.d+)", output)
        if match == None:
            raise ValueError(f'Unexpected firmware version format received: {output}.')
        model = match.group(1).strip()
        firmware_version = match.group(2).strip()
        return firmware_version
    
class fluke_9141(fluke_base):

    allowed_scan_modes = ["on", "off"]
    switch_states = ["open", "closed"]
    
    def set_scan_mode(self, mode: str) -> None:
        """
        Sets the scan mode to the currently open connection. Scan mode forces changes in temperature to adhere to the current scan rate.

        Args:
            mode: The scan mode 'on' or 'off'.

        Returns:
            None.
        """
        if mode.lower() not in self.allowed_scan_modes:
            raise ValueError(f'{mode} is not a valid scan mode. Must be {", ".join(self.allowed_scan_modes)}.')
        self.write('sc', mode.lower())
    
    def get_scan_mode(self) -> str:
        """
        Reads the current scan mode from currently open connection.

        Args:
            None.

        Returns:
            scan_mode: A string with the current scan mode 'on' or 'off'.
        """
        output = self.read('sc')
        if output == None:
            raise ValueError('Failed to receive data.')
        match = re.match(r"scan:\s+(ON|OFF)", output)
        if match == None:
            raise ValueError(f'Unexpected scan mode format received: {output}.')
        scan_mode = match.group(1).lower()
        return scan_mode

    def set_scan_rate(self, rate: float) -> None:
        """
        Sets the scan rate on the currently open connection.

        Args:
            rate: The scan rate in currently initialized temperature unit per minute.

        Returns:
            None.
        """
        self.write('sr', str(rate))

    def get_scan_rate(self) -> float:
        """
        Gets the current scan rate from currently open connection.

        Args:
            None.

        Returns:
            float: A floating point value representing the scan rate in currently initialized temperature unit per minute.
        """
        output = self.read('sr')
        if output == None:
            raise ValueError('Failed to receive data.')
        match = re.match(r"srat:\s+(\d+.\d+)", output)
        if match == None:
            raise ValueError(f'Unexpected scan rate format received: {output}.')
        scan_rate = float(match.group(1))
        return scan_rate
    
    def get_switch_hold(self) -> tuple[str, float]:
        """
        Reads the current switch hold status from currently open connection.

        Args:
            None.

        Returns:
            switch_state: A string with the current switch state 'open' or 'closed'.
            temperature: A floating point representation of the current temperature in the initialized temperature unit.
        """
        output = self.read('ho')
        if output == None:
            raise ValueError('Failed to receive data.')
        match = re.match(r"hold:\s+(open|closed),\s+(\d+.\d+)\s+[CF]", output)
        if match == None:
            raise ValueError(f'Unexpected switch hold format received: {output}.')
        switch_state = match.group(1).lower()
        temperature = float(match.group(2))
        return (switch_state, temperature)
    
    def set_high_limit(self, limit: float) -> None:
        """
        Sets the high limit on the currently open connection. The high limit is a safety feature that prevents the temperature source from exceeding a specified temperature.

        Args:
            limit: The high limit in the current temperature unit.

        Returns:
            None.
        """
        if type(limit) not in [int, float]:
            raise ValueError('High limit must be a number.')
        self.write('hl', str(round(limit)))

    def get_high_limit(self) -> int:
        """
        Reads the current high limit from currently open connection.

        Args:
            None.

        Returns:
            high_limit: An integer representation of the high limit in the current temperature unit.
        """
        output = self.read('hl')
        if output == None:
            raise ValueError('Failed to receive data.')
        match = re.match(r"hl:\s+(\d+)", output)
        if match == None:
            raise ValueError(f'Unexpected high limit format received: {output}.')
        high_limit = int(match.group(1))
        return high_limit

class fluke_6020(fluke_base):

    def get_vernier(self) -> float:
        """
        Reads the current vernier from currently open connection.

        Args:
            None.

        Returns:
            vernier: A floating point representation of the vernier.
        """
        output = self.read('v')
        if output == None:
            raise ValueError('Failed to receive data.')
        match = re.match(r"v:\s+(\d+.\d+)", output)
        if match == None:
            raise ValueError(f'Unexpected vernier format received: {output}.')
        vernier = float(match.group(1))
        return vernier
    
    def set_vernier(self, vernier: float) -> None:
        """
        Sets the vernier on the currently open connection. The user may want to adjust the set-point slightly to achieve a precise bath temperature. The set-point vernier allows one to adjust the temperature below or above the set-point by a small amount with very high resolution. 

        Args:
            vernier: A floating point representation of a 6 digit number with five digits after the decimal point. This is a temperature offset in degrees of the selected units, C or F.

        Returns:
            None.
        """
        if type(vernier) not in [int, float]:
            raise ValueError('Vernier must be a number.')
        if vernier < 0 or vernier > 9.99999:
            raise ValueError('Vernier must be between 0 and 9.99999.')
        self.write('v', str(vernier))

    def get_cutout(self) -> float:
        """
        Reads the current cutout from currently open connection.

        Args:
            None.

        Returns:
            cutout: A floating point representation of the cutout in the current temperature unit.
        """
        output = self.read('c')
        if output == None:
            raise ValueError('Failed to receive data.')
        match = re.match(r"c:\s+(\d+)\s+([CF]),\s+(in|out)", output)
        if match == None:
            raise ValueError(f'Unexpected cutout format received: {output}.')
        cutout = float(match.group(1))
        unit = match.group(2)
        if unit.lower() != self.__temperature_unit.lower():
            raise ValueError(f'Cutout unit mismatch. Expected {self.__temperature_unit}, received {unit}. Please restart the temperature source')
        cutout_status = match.group(3)
        if cutout_status == 'out':
            raise ValueError('Device is currently cut out.')
        return cutout
    
    def set_cutout(self, cutout: float) -> None:
        """
        Sets the cutout on the currently open connection.

        Args:
            cutout: The cutout in the current temperature unit.

        Returns:
            None.
        """
        if type(cutout) not in [int, float]:
            raise ValueError('Cutout must be a number.')
        self.write('c', str(cutout))