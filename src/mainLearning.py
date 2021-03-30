import datetime
import numpy as np

import os
import time

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

from ReconfigurationLearner.EnvironementCost import ReconfigurationEnvironement as environementCost
from ReconfigurationLearner.EnvironementSeuil import ReconfigurationEnvironement as environementSeuil
import param



import tensorflow as tf

from tf_agents.agents.dqn import dqn_agent
from tf_agents.environments import tf_py_environment
from tf_agents.networks import q_network
from tf_agents.policies import random_tf_policy
from tf_agents.replay_buffers import tf_uniform_replay_buffer
from tf_agents.trajectories import trajectory
from tf_agents.utils import common



#from tensorflow.python.training import checkpoint_utils as cp


tf.compat.v1.enable_v2_behavior()


def getPath(seuil, topoName, SliceDistrib, TopologySettings, stateVersion, rewardVersion, numberOfStepsByState, numberOfStepsForCost, name):
    dossier = os.path.join("..", "modelLR_Reconfiguration")
    if not os.path.exists(dossier):
        os.mkdir(dossier)
    if seuil:
        dossier = os.path.join(dossier, "seuil")
    else:
        dossier = os.path.join(dossier, "cost")
    if not os.path.exists(dossier):
        os.mkdir(dossier)
    dossier = os.path.join(dossier, topoName)
    if not os.path.exists(dossier):
        os.mkdir(dossier)
    dossier = os.path.join(dossier, "D{}-S{}".format(SliceDistrib,TopologySettings))
    if not os.path.exists(dossier):
        os.mkdir(dossier)
    dossier = os.path.join(dossier, "version{}-{}".format(stateVersion, rewardVersion))
    if not os.path.exists(dossier):
        os.mkdir(dossier)
    dossier = os.path.join(dossier, "step{}-vision{}".format(numberOfStepsByState, numberOfStepsForCost))
    if not os.path.exists(dossier):
        os.mkdir(dossier)
    dossier = os.path.join(dossier, name)
    if not os.path.exists(dossier):
        os.mkdir(dossier)
    return dossier


"""
        Recover the biggest training number inside a directory
"""
def biggerNumberToLoad(path):
    listFile = os.listdir(path)
    biggest = 0
    for file in listFile :
        if file[-5:] == "index":
            number = file[:-6]
            number = number[6:]
            number = int(float(number))
            if number > biggest:
                biggest = number
        
    return biggest


"""
        Save a training
"""
def saveTraining(dossier, listInstanceAlreadyTrained, gamma, seuilReconf, checkpoint):
    
    checkpoint.save(os.path.join(dossier,"agent"))
    
    file = open(os.path.join(dossier, "info.txt"),'w')
    file.write("{}\n".format(gamma))
    file.write("{}\n".format(seuilReconf))
    file.write("{}\n".format(listInstanceAlreadyTrained))
    file.close
    
    
"""
        The the details of a trained instance inside a log file
"""
def saveLog(dossier,num, temps, reward, nbReconf, loss, lossPerReconf, profit):
    with open(os.path.join(dossier, "log"), "a") as myfile:
        myfile.write("Instance {} time {} reward {} nbReconf {} loss {} loss/reconf {} profit {}\n".format(num, temps, reward, nbReconf, loss, lossPerReconf, profit))
    
    
"""
        Load a training
"""
def loadTraining(seuil, topoName, SliceDistrib, TopologySettings, stateVersion, rewardVersion, numberOfStepsByState, numberOfStepsForCost, name, env, checkpoint, number):
    dossier = getPath(seuil, topoName, SliceDistrib, TopologySettings, stateVersion, rewardVersion, numberOfStepsByState, numberOfStepsForCost, name)
    
    checkpoint.restore(os.path.join(dossier,"agent-{}".format(number)))
    #checkpoint.restore(os.path.join(path,"agent-{}".format(number))).assert_consumed()

    file = open(os.path.join(dossier, "info.txt"),'r')
    line = file.readline()
    line = line.replace("\n","")
    gamma = float(line)
    line = file.readline()
    line = line.replace("\n","")
    ratioPriceSeuilReconf = float(line)
    line = file.readline()
    line = line.replace("\n","")
    line = line.replace("[","")
    line = line.replace("]","")
    line = line.replace("'","")
    listInstanceAlreadyTrained = line.split(", ")
    file.close
    
    env.loadInstanceAlreadyTrained(listInstanceAlreadyTrained)
    
    return gamma, ratioPriceSeuilReconf


def compute_avg_return(environment, policy, num_episodes=10):
    total_return = 0.0
    listReturns = []
    for i in range(num_episodes):
        
    
        time_step = environment.reset()
        episode_return = 0.0
    
        while not time_step.is_last():
            action_step = policy.action(time_step)
            time_step = environment.step(action_step.action)
            episode_return += time_step.reward
            
        total_return += episode_return
        listReturns.append(episode_return.numpy()[0])
        print("    Eval Episode {}    {}".format(i+1, episode_return.numpy()[0]))
    
    avg_return = total_return / num_episodes
    return avg_return.numpy()[0], listReturns


def collect_step(environment, policy, buffer):
    time_step = environment.current_time_step()
    action_step = policy.action(time_step)
    next_time_step = environment.step(action_step.action)
    traj = trajectory.from_transition(time_step, action_step, next_time_step)
    
    # Add trajectory to the replay buffer
    buffer.add_batch(traj)


def collect_data(env, envPy, policy, buffer, nbSteps):
    for i in range(nbSteps):
        collect_step(env, policy, buffer)
        if envPy._episode_ended:
            break
        #print("Collect_data {}".format(i))
        
def initEnv(seuil, newTopo, topoName, SliceDistrib, TopologySettings, listInstanceFiles, ratioPriceSeuilReconf, stateVersion, rewardVersion, nbStepsReconf = 3, gamma = 0.9, beta = 0, numberOfStepsByState = 1, numberOfStepsForCost = 1, evaluation = False, dossierToSave = None):
    if seuil:
        env = environementSeuil(True, newTopo, topoName, SliceDistrib, TopologySettings, listInstanceFiles, stateVersion, rewardVersion, nbStepsReconf, ratioPriceSeuilReconf, numberOfStepsByState = numberOfStepsByState, numberOfStepsForCost = numberOfStepsForCost, evaluation = evaluation, dossierToSave = dossierToSave)
    else:
        env = environementCost(True, newTopo, topoName, SliceDistrib, TopologySettings, listInstanceFiles, stateVersion, rewardVersion, nbStepsReconf, ratioPriceSeuilReconf, numberOfStepsByState = numberOfStepsByState, numberOfStepsForCost = numberOfStepsForCost, evaluation = evaluation, dossierToSave = dossierToSave)
    env.setGammaDiscount(gamma)
    env.setBeta(beta)
    tf_env = tf_py_environment.TFPyEnvironment(env)
    
    return env, tf_env


def createQNetwork(env):
    
    fc_layer_params = (64,64)
    
    #BatchNormalization layer
    preprocessing_layer =  tf.keras.layers.BatchNormalization(
    axis=-1,
    momentum=0.99,
    epsilon=0.001,
    center=True,
    scale=True,
    beta_initializer="zeros",
    gamma_initializer="ones",
    moving_mean_initializer="zeros",
    moving_variance_initializer="ones",
    beta_regularizer=None,
    gamma_regularizer=None,
    beta_constraint=None,
    gamma_constraint=None,
    renorm=False,
    renorm_clipping=None,
    renorm_momentum=0.99,
    fused=None,
    trainable=True,
    virtual_batch_size=None,
    adjustment=None,
    name=None)


    q_net = q_network.QNetwork(
        env.observation_spec(),
        env.action_spec(),
        preprocessing_layers=preprocessing_layer,
        fc_layer_params=fc_layer_params)
    
    return q_net




"""        ****************************************************************************************************************************************    """
"""                Main                                                                                                                                """
"""        ****************************************************************************************************************************************    """


if __name__ == '__main__':
    
    tTot = time.time()
    
    """
            Parameters for reconfiguration and network initialization
            Not usefull to modify
    """
    ReconfGCLp = [1]
    SliceDistrib = "4"
    TopologySettings = "6"
    useMBB = True
    param.stableCycle = 10
    listInstanceFiles = []
    listInstanceEval = []
    beta = 1                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        
    
    stateVersion = 5                #Parameters version
    rewardVersion = 3               #Reward version
    seuil = False                   #Always False
    newTopo = False                 #Always False
    
    numberOfStepsByState = 5        #Number of time step between two action state
    numberOfStepsForCost = 15       #Number of time step used to compute the reward. Must be >= numberOfStepsByState
    
    ratioPriceSeuilReconf = 1500    #Cost of a reconfiguration (this will be multiply by numberOfStepsForCost)
    
    
    """
            HyperParameters
    """
    batch_size = 288
    learning_rate = 1e-3
    gamma = 0.9
    replay_buffer_max_length = int(1440*50/numberOfStepsByState)    #1440/numberOfStepsByState : 1440 time steps for an instance = 288 action states
    initial_collect_steps = 96  # @param {type:"integer"} 
    collect_steps_per_iteration = 32  # @param {type:"integer"}     #Number of state between each gradient descend
    #collect_steps_per_iteration = 16  # @param {type:"integer"}
    
    
    """
            Optimizer and epsilon greedy
    """
    global_step = tf.compat.v1.train.get_or_create_global_step()
    start_epsilon = 0.99
    n_of_steps = int(1440*300/collect_steps_per_iteration/numberOfStepsByState)     #Training = 300 instances (1440 time steps / numberOfStepsByState / Number of state between each gradient descend
    end_epsilon = 0.00
    epsilon = tf.compat.v1.train.polynomial_decay(start_epsilon,global_step,n_of_steps,end_learning_rate=end_epsilon)
    train_step_counter = tf.compat.v1.train.get_or_create_global_step()
    optimizer = tf.optimizers.Adam(learning_rate=learning_rate)                     #Adam Optimizer
    

    
    
    if seuil:
        nameSave = "testSeuil{}".format(ratioPriceSeuilReconf)
        print("Environement Seuil Not up to date")
        exit()
    else:
        nameSave = "testCost{}".format(ratioPriceSeuilReconf)
    
    
    SliceDistrib = "Real"
    TopologySettings = "Real"
    topoName = "ta1"
    for i in range(1,301):
        listInstanceFiles.append("dynamic-DReal-TReal-Train-{}".format(i))      #Instances for the training
    for i in range(1,4):
        listInstanceEval.append("dynamic-DReal-TReal-Eval-{}".format(i))        #Instances for the evaluation

    
    """
            Creation of the training environment
    """
    env, train_env = initEnv(seuil, newTopo, topoName, SliceDistrib, TopologySettings, listInstanceFiles, ratioPriceSeuilReconf, stateVersion, rewardVersion, nbStepsReconf = 3, gamma = gamma, beta = beta, numberOfStepsByState = numberOfStepsByState, numberOfStepsForCost = numberOfStepsForCost)
    
    """
            Creation of the neural network
    """
    q_net = createQNetwork(train_env)
    
    """
            Creation of the DQN Agent
    """
    agent = dqn_agent.DqnAgent(
        train_env.time_step_spec(),
        train_env.action_spec(),
        q_network=q_net,
        epsilon_greedy=epsilon,
        optimizer=optimizer,
        td_errors_loss_fn=common.element_wise_squared_loss,
        train_step_counter=train_step_counter)
    agent.initialize()
    
    """
            Creation of the replay buffer
    """
    replay_buffer = tf_uniform_replay_buffer.TFUniformReplayBuffer(
        data_spec=agent.collect_data_spec,
        batch_size=train_env.batch_size,
        max_length=replay_buffer_max_length)
    
    """
            Initialization of the checkpoint
    """
    checkpoint = tf.train.Checkpoint(model=agent, optimizer=optimizer, replay_buffer=replay_buffer)
    
    """
            Initial policy
    """
    random_policy = random_tf_policy.RandomTFPolicy(train_env.time_step_spec(),train_env.action_spec())
    initPolicy = random_policy
    agent.train = common.function(agent.train)
    # Reset the train step
    agent.train_step_counter.assign(0)
    
    """
            Loading of the training
    """
    #We get the path of the save directory
    dossierPath = getPath(seuil, topoName, SliceDistrib, TopologySettings, stateVersion, rewardVersion, numberOfStepsByState, numberOfStepsForCost, nameSave)
    numberToLoad = biggerNumberToLoad(dossierPath)      #We reconver the biggest training number (if it exist)
    toLoad = False
    if numberToLoad > 0:
        toLoad = True
    if toLoad :     #If there is a training to load
        print("    ####################    ")
        print("      Loading number {}    ".format(numberToLoad))
        print("    ####################    ")
        #We load the checkpoint (qnetwork, optimizer, epsilon, replay_buffer) and some parameters
        gamma, ratioPriceSeuilReconf = loadTraining(seuil, topoName, SliceDistrib, TopologySettings, stateVersion, rewardVersion, numberOfStepsByState, numberOfStepsForCost, nameSave, env, checkpoint, numberToLoad)
        env.setSeuilReconf(ratioPriceSeuilReconf)
        env.setGammaDiscount(gamma)
        eval_policy = agent.policy
        collect_policy = agent.collect_policy
    else:       #If there is no training to load
        eval_policy = agent.policy
        collect_policy = agent.collect_policy
        collect_data(train_env, env, initPolicy, replay_buffer, initial_collect_steps)      #We collect the first data
        print("Initiale Collect : OK")
    
    dataset = replay_buffer.as_dataset(
        num_parallel_calls=3, 
        sample_batch_size=batch_size, 
        num_steps=2).prefetch(3)
    iterator = iter(dataset)


    returns = []
    
    """
            Used to test an already trained agent
    """
    if False :
        #Evaluate the agent's policy once before training.
        dossierToSave = os.path.join(getPath(seuil, topoName, SliceDistrib, TopologySettings, stateVersion, rewardVersion, numberOfStepsByState, numberOfStepsForCost, nameSave), str(numberToLoad))
        if not os.path.exists(dossierToSave):
            os.mkdir(dossierToSave)
        env2, eval_env = initEnv(seuil, newTopo, topoName, SliceDistrib, TopologySettings, listInstanceEval[:], ratioPriceSeuilReconf, stateVersion, rewardVersion, nbStepsReconf = 3, gamma = gamma, beta = beta, numberOfStepsByState = numberOfStepsByState, numberOfStepsForCost = numberOfStepsForCost, evaluation = True, dossierToSave = dossierToSave)
        avg_return, listReturns = compute_avg_return(eval_env, agent.policy, len(listInstanceEval))
        print('Initial Return = {}'.format(avg_return))
        returns = [avg_return]
        exit()
    
    
    """
            Training Loop
    """
    t = time.time()
    n = 0
    loss_total = 0
    while env.doStillRunning():
        # Collect a few steps using collect_policy and save to the replay buffer.
        collect_data(train_env, env, agent.collect_policy, replay_buffer, collect_steps_per_iteration)
        
        # Sample a batch of data from the buffer and update the agent's network.
        experience, unused_info = next(iterator)
        train_loss = agent.train(experience).loss
        loss_total+=train_loss
        step = agent.train_step_counter.numpy()
        
        #print('        step = {0}: loss = {1}'.format(step, train_loss))
        
        #Every instances, we save the training
        if env._episode_ended:
            print("    Instance {} fini en {}s    total loss {}    avgLoss per reconf {}".format(env.listInstanceAlreadyTrained[-1],time.time()-t, loss_total, loss_total/float(sum(env.reconfsDone))))
            print("")
            dossier = getPath(seuil, topoName, SliceDistrib, TopologySettings, stateVersion, rewardVersion, numberOfStepsByState, numberOfStepsForCost, nameSave)
            saveTraining(dossier, env.listInstanceAlreadyTrained, gamma, ratioPriceSeuilReconf, checkpoint)
            saveLog(dossier,env.listInstanceAlreadyTrained[-1], time.time()-t, env.rewardTotal, sum(env.reconfsDone), loss_total, loss_total/float(sum(env.reconfsDone)), (env.allocateur.accprofit[-1]-(sum(env.reconfsDone)*numberOfStepsForCost*ratioPriceSeuilReconf)))
            t = time.time()
            loss_total = 0
           
        #Every 50 instances we evaluate the agent
        if env._episode_ended and (len(env.listInstanceAlreadyTrained) % 50 == 0 and len(env.listInstanceAlreadyTrained) >=100 ):
            dossierToSave = os.path.join(getPath(seuil, topoName, SliceDistrib, TopologySettings, stateVersion, rewardVersion, numberOfStepsByState, numberOfStepsForCost, nameSave), str(len(env.listInstanceAlreadyTrained)))
            if not os.path.exists(dossierToSave):
                os.mkdir(dossierToSave)
            env2, eval_env = initEnv(seuil, newTopo, topoName, SliceDistrib, TopologySettings, listInstanceEval[:], ratioPriceSeuilReconf, stateVersion, rewardVersion, nbStepsReconf = 3, gamma = gamma, beta = beta, numberOfStepsByState = numberOfStepsByState, numberOfStepsForCost = numberOfStepsForCost, evaluation = True, dossierToSave = dossierToSave)
            avg_return, listReturns = compute_avg_return(eval_env, agent.policy, len(listInstanceEval))
            print('    step = {0}: Average Return = {1}'.format(step, avg_return))
            returns.append(avg_return)
            print("")
            
        
            
        n += 1
        

    print("Total time {}".format(time.time()-tTot))


    
    