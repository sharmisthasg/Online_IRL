import numpy as np

from .spaces import *
from .transition import *

from itertools import product


class AbstractEnvironment:
    """
    An AbstractEnvironment describes the minimal components needed for an
    environment, specifically, state and action spaces, and transition function.
    """

    def __init__(self):
        """
        No initialization required by AbstractEnvironment.
        """

        pass

    def reset(self):
        """
        Reset the environment to the initial state
        """

        raise NotImplementedError

    def act(self, action):
        """
        Perform the action on the current state

        action - action number to perform

        returns - state transitioned into
        """

        raise NotImplementedError

    def addTerminalState(self, state):
        """
        Indicate that a particular state is a terminal state
        """

        raise NotImplementedError

    def isTerminal(self, state):
        """
        Indicate if the provided state is a terminal state.
        """

        raise NotImplementedError

    def __str__(self):
        """
        String representation of environment
        """

        return "AbstractEnvironment"


class DiscreteEnvironment(AbstractEnvironment):
    """
    A DiscreteEnvironment has a finite set of discrete states and actions.
    States and actions are represented in a DiscreteSpace.
    """

    def __init__(self, stateSpace, actionSpace, initial_state=None, TransitionClass=DiscreteTransition):
        """
        Create a discrete environment, defined by the provided states and
        actions.

        stateSpace    - state space of the environment.  Must be a DiscreteSpace
        actionSpace   - action space of the environment.  Must be a DiscreteSpace
        initial_state - the default state to reset to
        """

        # Store the state and action space
        self.stateSpace = stateSpace
        self.actionSpace = actionSpace

        # Set up the transition function, reward and terminal states
        self.transition = TransitionClass(self.stateSpace.size(), self.actionSpace.size())
        self.terminalStates = set()

        # If an initial state is not provided, simply assume the first state in
        # the state space
        if initial_state is None:
            self.initial_state = self.stateSpace[0]
        else:
            self.initial_state = initial_state

        # The current state the agent is in
        self.current_state = self.initial_state

    def enumerate(self, state, action=None, nextState=None):
        """
        Convert the existing (state, action, nextState) tuple into an enumeration
        of each element from the corresponding state and action spaces.

        Example:
             Assume a stateSpace which enumerates 'a' -> 1 and 'c' -> 4, and an
             actionSpace which enumerates 'x' -> 7

             >>> env.enumerate('a', 'x', 'c')
             (1, 7, 4)
             >>> env.enumerate('c')
             (4,)
             >>> env.enumerate('c', 'x')
             (4, 7)
        """

        # TODO:  Assert that state, action, and nextState are in respective spaces

        enumeration = (self.stateSpace(state),)

        if action is not None:
            enumeration = enumeration + (self.actionSpace(action),)

        if nextState is not None:
            enumeration = enumeration + (self.stateSpace(nextState),)

        return enumeration

    def reset(self):
        """
        Place the agent into the initial state
        """

        self.current_state = self.initial_state

    def act(self, action):
        """
        Perform the action in the current state
        """

        # Calculate the next state from the transition
        nextStateNum = self.transition.sample(self.stateSpace(self.current_state), self.actionSpace(action))

        self.current_state = self.stateSpace[nextStateNum]

        # Return the current state
        return self.current_state

    def addTerminalState(self, state):
        """
        Indicate that a particular state is a terminal state
        """

        # TODO: Ensure the terminal state is in the state space

        self.terminalStates.add(state)

    def isTerminal(self, state):
        """
        Check if the state is a terminal state
        """

        return state in self.terminalStates

    def __str__(self):
        """
        String representation of the environment
        """

        return "Discrete Environment\n   Number of States:   %d\n   Number of Actions:  %d" % (
            self.num_states, self.num_actions)


class GraphWorld(DiscreteEnvironment):
    """
    A Graphworld environment defines a 2D grid world.  States are symbolically
    represented as the (x,y) position of an agent in the world.  Actions consist
    of a list of the connected nodes.  Additionally, grid cells can be blocked.
    """

    def __init__(self, shape, radius, initial_state=None, can_stay=True, blocked=None,
                 TransitionClass=DiscreteTransition):
        self.shape = shape
        self.radius = radius
        # States are defined as (x,y) positions in the world,
        # actions are a list of connected nodes
        states = [(x, y) for x in range(self.shape[0]) for y in range(self.shape[1])]
        actions = [(i, j) for i in range(-radius, radius + 1) for j in range(-radius, radius + 1)]
        if not can_stay:
            actions.remove((0, 0))

        # Create a set of the blocked cells in the environment
        self.blocked_cells = set()

        if blocked is not None:
            for x, y in states:
                if blocked[x, y] != 0:
                    self.blocked_cells.add((x, y))

        # Remove blocked cells from the state space
        for x, y, in self.blocked_cells:
            states.remove((x, y))

        # Call the DiscreteEnvironment initializer, passing the states and
        # actions wrapped as DiscreteSpaces.  This initializes the stateSpace,
        # actionSpace, transition and terminal_state attributes.

        DiscreteEnvironment.__init__(self, DiscreteSpace(states),
                                     DiscreteSpace(actions),
                                     initial_state=initial_state,
                                     TransitionClass=TransitionClass)

        # Populate the transition functions
        for state, action in [(s, a) for s in self.stateSpace for a in self.actionSpace]:
            self.__set_transitions(state, action)

    def __set_transitions(self, state, action):
        """
        Creates the entries in the transition function for the given state and action
        """
        # Extract x and y to calculate the position of the next state
        x, y = state
        x += action[0]
        y += action[1]

        # Check if the new x,y maps to a valid state.  If not, next_state should
        # simply be the original state
        if (x, y) not in self.stateSpace or (x, y) in self.blocked_cells:
            x, y = state

        # Populate the transition function
        self.transition[self.enumerate(state, action, (x, y))] = 1.0

    def __str__(self):
        """
        String representation of the environment
        """

        return "Graphworld Environment\n   World Shape: (%d, %d)\n   Can Stay:    %s" % (
            self.shape[0], self.shape[1], 'True' if 'stay' in self.actions else 'False')


class Gridworld(DiscreteEnvironment):
    """
    A Gridworld environment defines a 2D grid world.  States are symbolically
    represented as the (x,y) position of an agent in the world.  Actions consist
    of 'up', 'down', 'left', 'right', and optionally 'stay'.  Additionally, grid
    cells can be blocked.
    """

    def __init__(self, shape, initial_state=None, can_stay=True, blocked=None, TransitionClass=DiscreteTransition):
        """
        Create a gridworld with the given size.  States are defined as (x,y)
        values, actions are in the set ['up','down','left','right','stay']

        shape         - tuple defining the size of the world: (width, height)
        initial_state - (optional) start state of the agent in the environment
                                        Default to (0,0)
        can_stay      - indicates if the agent has an option to stay in the same
                                        location as an action.  Default is True
        blocked       - a 2D array-like indicating which cells are blocked.
                                        Shape of the array should match the shape parameter;
                                        blocked grids are indicated by a non-zero entry.
        """

        # Store the size of the world, and create state and action spaces for the
        # SymbolicEnvironment initializer
        self.shape = shape

        # States are defined as (x,y) positions in the world,
        # actions are "UP", "DOWN", "LEFT", "RIGHT", "STAY".
        states = [(x, y) for x in range(self.shape[0]) for y in range(self.shape[1])]
        actions = ['up', 'right', 'down', 'left']
        if can_stay:
            actions.append('stay')

        # Create a set of the blocked cells in the environment
        self.blocked_cells = set()

        if blocked is not None:
            for x, y in states:
                if blocked[x, y] != 0:
                    self.blocked_cells.add((x, y))

        # Remove blocked cells from the state space
        for x, y, in self.blocked_cells:
            states.remove((x, y))

        # Call the DiscreteEnvironment initializer, passing the states and
        # actions wrapped as DiscreteSpaces.  This initializes the stateSpace,
        # actionSpace, transition and terminal_state attributes.

        DiscreteEnvironment.__init__(self, DiscreteSpace(states),
                                     DiscreteSpace(actions),
                                     initial_state=initial_state,
                                     TransitionClass=TransitionClass)

        # Populate the transition functions
        for state, action in [(s, a) for s in self.stateSpace for a in self.actionSpace]:
            self.__set_transitions(state, action)

    def __set_transitions(self, state, action):
        """
        Creates the entries in the transition function for the given state and action
        """

        # Extract x and y to calculate the position of the next state
        x, y = state

        # Update x and y based on actions
        x += {'left': -1, 'right': 1}.get(action, 0)
        y += {'up': -1, 'down': 1}.get(action, 0)

        # Check if the new x,y maps to a valid state.  If not, next_state should
        # simply be the original state
        if (x, y) not in self.stateSpace or (x, y) in self.blocked_cells:
            x, y = state

        # Populate the transition function
        self.transition[self.enumerate(state, action, (x, y))] = 1.0

    def __str__(self):
        """
        String representation of the environment
        """

        return "Gridworld Environment\n   World Shape: (%d, %d)\n   Can Stay:    %s" % (
            self.shape[0], self.shape[1], 'True' if 'stay' in self.actions else 'False')


class NoisyGridworld(Gridworld):
    """
    A NoisyGridworld environment extends the base gridworld by moving agents to
    a random neighboring cell at each step with a predefined probability.
    """

    def __init__(self, shape, initial_state=None, can_stay=True, blocked=None, noise=0.1,
                 TransitionClass=SparseTransition):
        """
        Create a gridworld with the given size.  States are defined as (x,y)
        values, actions are in the set ['up','down','left','right','stay']

        shape         - tuple defining the size of the world: (width, height)
        initial_state - (optional) start state of the agent in the environment
                                        Default to (0,0)
        can_stay      - indicates if the agent has an option to stay in the same
                                        location as an action.  Default is True
        blocked       - a 2D array-like indicating which cells are blocked.
                                        Shape of the array should match the shape parameter;
                                        blocked grids are indicated by a non-zero entry.
        noise         - Probability of moving to a random neighboring cell when
                                        an action is taken.
        """

        # Initialize the Gridworld
        Gridworld.__init__(self, shape, initial_state=initial_state,
                           can_stay=can_stay, blocked=blocked, TransitionClass=TransitionClass)

        self.noise = noise

        # Upldate the transition function to include random noise
        for state, action in [(s, a) for s in self.stateSpace for a in self.actionSpace]:
            self.__update_transitions(state, action, noise)

    def __update_transitions(self, state, action, noise):
        """
        Redistribute the probability distribution over next states to include
        random motion to available neighboring states, as well as possibly
        staying in the same cell
        """

        valid_next_states = set()

        # Calculate valid next states
        for dx, dy in [(0, 0), (0, -1), (0, 1), (-1, 0), (1, 0)]:
            # What is the next state (x and y values)?
            x = state[0] + dx
            y = state[1] + dy

            # Decrease the probability of transitioning into next_state by 1-noise
            if (x, y) in self.stateSpace:
                self.transition[self.enumerate(state, action, (x, y))] *= (1 - noise)

            # Determine if the next state is a valid transition
            if (x, y) in self.stateSpace and (x, y) not in self.blocked_cells:
                valid_next_states.add((x, y))

        # Increase the chance of transitioning into each valid next state by
        # noise / valid_states
        for nextState in valid_next_states:
            self.transition[self.enumerate(state, action, nextState)] += noise / len(valid_next_states)

    def __str__(self):
        """
        String representation of the environment
        """

        return "Noisy Gridworld Environment\n   World Shape: (%d, %d)\n   Can Stay:    %s\n   Noise Level: %f" % (
            self.shape[0], self.shape[1], 'True' if 'stay' in self.actions else 'False', self.noise)


class Taskworld(DiscreteEnvironment):
    """
    A Taskworld environment is similar to a Gridworld environment, in that it
    defines a 2D grid world.  States are symbolically represented as the (x,y)
    position of an agent in the world, augmented by a binary list of specific
    tasks to be completed.  Actions consist of 'up', 'down', 'left', 'right',
    'operate', and optionally 'stay'.  Grid cells can be blocked.

    Tasks are associated with specific grid cells, with one task per grid cell.
    When operate is performed on the grid cell, it sets the task as complete.

    Note that the state space of the environment grows exponentially with the
    number of tasks.
    """

    def __init__(self, shape, taskLocations, initial_state=None, can_stay=True, blocked=None,
                 TransitionClass=SparseTransition):
        """
        Create a taskworld with the given size and number of tasks.  States are
        defined as the cross-product of (x,y) corrdinates and a binary vector of
        task completion.  Actions are in the set ['up','down','left','right',
        'operate','stay']

        shape         - tuple defining the size of the world: (width, height)
        taskLocations - location of where tasks are to be completed
        initial_state - (optional) start state of the agent in the environment
                                        Default to (0,0)
        can_stay      - indicates if the agent has an option to stay in the same
                                        location as an action.  Default is True
        blocked       - a 2D array-like indicating which cells are blocked.
                                        Shape of the array should match the shape parameter;
                                        blocked grids are indicated by a non-zero entry.
        TransitionClass - Which class of transition function to use.  Default to
                                            SparseTransition.
        """

        # Store the size of the world, and create state and action spaces for the
        # SymbolicEnvironment initializer
        self.shape = shape

        # Where are tasks located?  Set to (-1,-1) to indicate that task location
        # has not been assigned yet.
        self.taskLocations = taskLocations
        self.numTasks = len(taskLocations)
        self.taskComplete = [False] * self.numTasks

        # Task completion vectors are defined as binary tuples indicating which
        # tasks are complete.
        taskSpace = list(product([False, True], repeat=self.numTasks))

        self.locations = [(x, y) for x in range(self.shape[0]) for y in range(self.shape[1])]

        # Create a set of the blocked cells in the environment
        # TODO: Remove blocked cells from the stateSpace, to speed up value iteration
        self.blocked_cells = set()

        if blocked is not None:
            for x, y in self.locations:
                if blocked[x, y] != 0:
                    self.blocked_cells.add((x, y))  # Add this as a blocked cell

        for x, y in self.blocked_cells:
            self.locations.remove((x, y))  # Remove from possible locations

        # States are defined as all possible combinations of locations and task
        # completion states
        states = [(location, task) for location in self.locations for task in taskSpace]

        actions = ['up', 'right', 'down', 'left', 'operate']
        if can_stay:
            actions.append('stay')

        # Call the DiscreteEnvironment initializer, passing the states and
        # actions wrapped as DiscreteSpaces.  This initializes the stateSpace,
        # actionSpace, transition and terminal_state attributes.

        DiscreteEnvironment.__init__(self, DiscreteSpace(states),
                                     DiscreteSpace(actions),
                                     initial_state=initial_state,
                                     TransitionClass=TransitionClass)

        # Populate the transition functions
        for state, action in [(s, a) for s in self.stateSpace for a in self.actionSpace]:
            self.__set_transitions(state, action)

    def __set_transitions(self, state, action):
        """
        Creates the entries in the transition function for the given state and action
        """

        # Extract location to calculate the position of the next state, and task
        # completion to calculate the effect of operate actions
        location, task = state
        x, y = location

        # Update x and y based on actions
        x += {'left': -1, 'right': 1}.get(action, 0)
        y += {'up': -1, 'down': 1}.get(action, 0)

        # Check if the new x,y maps to a valid state.  If not, next_state should
        # simply be the original state
        if (x, y) not in self.locations or (x, y) in self.blocked_cells:
            x, y = location

        # See what to do if an operation is performed
        if action == 'operate' and location in self.taskLocations:
            # Set the completion of the task at this location to True
            task = list(task)
            taskIndex = self.taskLocations.index(location)
            task[taskIndex] = True
            task = tuple(task)

        # Populate the transition function
        self.transition.set(self.stateSpace(state), self.actionSpace(action), self.stateSpace(((x, y), task)), 1.0)

    def __str__(self):
        """
        String representation of the environment
        """

        return "Taskworld Environment\n   World Shape: (%d, %d)\n   Can Stay:    %s" % (
            self.shape[0], self.shape[1], 'True' if 'stay' in self.actions else 'False')
