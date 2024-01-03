
from Logger import *
from Experiment import *


class ExpControl:
    """ This class handles the control of session/stim from 2pmaster"""

    def __init__(self, logger):
        self.timer = None
        self.params = None
        self.exprmt = None
        self.logger = logger
        self.logger.setup_experiment_schema() # dj.create_virtual_module('experiment', 'pipeline_experiment')
        self.prev_command = None
        self.logger.update_setup_state('systemReady')

    def do_run_trial(self):
#       self.timer.start()

        self.exprmt.pre_trial()

#        print(self.timer.elapsed_time())

        # # # # # Trial period # # # # #
        self.timer.start()  # Start countdown for response]
        while self.timer.elapsed_time() < self.params['trial_duration'] * 1000 and \
                        self.logger.get_setup_state_control() == 'startStim' and self.exprmt.run():  # response period
            break_trial = self.exprmt.trial()  #  return true if trial is done
            if break_trial:
                break  # break if experiment calls for it
            systime.sleep(0.001)

#        print(self.timer.elapsed_time())

        # # # # # Post-Trial Period # # # # #
        self.exprmt.post_trial()

        # # # # # Intertrial period # # # # #
        while self.timer.elapsed_time() < self.params['intertrial_duration'] * 1000:
            self.exprmt.inter_trial()

    def do_initialize(self):
        """Initialize the stimulation software"""
        if not self.logger.get_setup_state() == 'systemReady':
            if self.logger.get_setup_state() == 'sessionRunning':
                self.do_stop_session()
            elif self.logger.get_setup_state() == 'stimRunning':
                self.do_stop_stim()
            else:
                pass
            self.logger.update_setup_state('systemReady')

    def do_start_session(self):
        """start stimulation session"""
        if not self.logger.get_setup_state() == 'sessionRunning':
            self.logger.init_params()  # clear settings from previous session
            self.logger.log_session()  # start session
            self.logger.update_setup_state('sessionRunning')
            self.params = (Task() & dict(task_idx=self.logger.task_idx)).fetch1()  # get parameters
            self.timer = Timer()  # main timer for trials
            self.exprmt = eval(self.params['exp_type'])(self.logger, self.timer, self.params)  # get PyMouse.experiment & init

    def do_start_stim(self):
        """start stimulation trials"""
        if not self.logger.get_setup_state() == 'stimRunning':
            self.exprmt.prepare()  # open stimulus window and prepare the protocol
            self.logger.update_setup_state('stimRunning')
            systime.sleep(1)
            while self.logger.get_setup_state_control() == 'startStim' and self.exprmt.run():
                self.logger.ping()
                self.do_run_trial()
            if not self.exprmt.run():  # stop if trials ended
                self.do_stop_stim()

    def do_stop_stim(self):
        # # # # # Cleanup # # # # #
        if self.logger.get_setup_state() == 'stimRunning':
            self.exprmt.cleanup()  # close the window and cleanup after the protocol run
            self.logger.update_setup_state('sessionRunning')

    def do_stop_session(self):
        if self.logger.get_setup_state() == 'sessionRunning' or self.logger.get_setup_state() == 'stimRunning':
            self.do_stop_stim()  # first stop the stimulaton
            self.logger.update_setup_state('systemReady')

    def process_command(self, command):
        if not command == self.prev_command:  # only process changes in command
            #   process command
            self.prev_command = command
            if command == 'Initialize':
                # wait for initialization
                self.do_initialize()
            elif command == 'startSession':
                self.do_start_session()
            elif command == 'startStim':
                self.exprmt.on_hold(False)  # undo stuff
                self.do_start_stim()  # this is a busy loop
            elif command == 'stopStim':
                self.do_stop_stim()
            elif command == 'stopSession':
                self.do_stop_session()
            else:
                pass

        elif (command == 'Initialize' or command == 'stopStim') and self.exprmt is not None:  # Trying to catch the period in between scans
            self.exprmt.on_hold()

