# Slices-Reconf-Learning

Codé en python 3.6
Utilise Cplex 12.* et tensorflow 2



Dossier instances (A DEZIPER) :

	Contient les topologies, les instances ainsi que les paramètres des fonctions
	
Dossier resultsCSV :

	Contient les résultats des instances (hors ceux réalisés par l'agent)
	Pour chaque algo : deux types de fichier csv :
		global.csv contient les résultats globaux résumés d'une instance
		local.csv contient pour chaque time steps l'état du réseau
		
Dossier modelLR_Reconfiguration :

	Contient les sauvegardes d'entrainement ainsi que les résultats de l'agent sur les instances d'évaluation
	A l'interieur d'un dossier d'experience : exemple testCost2000
		Les dossiers d'évalutation (100, 150, 200, ...) contiennent les résultats (.csv) de l'agents sur les instances d'évaluation. Le numéro correspond au numéro de l'agent entrainé, plus il est grand plus l'agent est entrainé.
		Les fichiers d'entrainement de l'agent : agent-number.data-00000-of-00001 et agent-number.index
		info.txt : fichier contenant le gamma discount, le prix de la reconfiguration et la liste des instances déjà entrainées.
		log : fichier de log
		analyseLog.py : permet de visualier le log sous forme de coubes.
		
Dossier src : contient les sources -> Fichiers intéréssants ici = mainDynamic.py, mainLearning.py, ReconfigurationLearner\EnvironementCostEnvironementCost.py

	allocation : fichiers qui gèrent l'allocation des slices, ainsi que les sous-problèmes de la génération de colonnes
	Chooser : classes qui permettent de choisir le béta de l'allocation/reconfiguration (projet avorté) ainsi que de choisir la fréquence de reconfiguration
	reconfiguration : Fichiers qui gèrent la reconfiguration en génération de colonnes
	Util : fonctions utilitaires
	ReconfigurationLearner : différents environements utilisé pour le learning (seul EnvironementCost.py est util maintenant)
	AllocateurDynamic.py : class qui gère la sauvegarde de l'état du réseau au fur et à mesure d'une instance (permet l'enregistrment des résultats)
	initializeNetworkDynamic.py : gère l'initialisation des capacités du réseau.
	param.py : paramètres util à la reconfiguration et à l'initialisation du réseau
	
	mainDynamic : Fichier main permettant de lancer des expériences (hors learning) sur des instances d'une journée.
		Permet de récupérer les résultats pour NoReconf ainsi que pour la réconf avec différentes fréquences
		
	mainLearning : Fichier main permettant l'entrainement et le test d'un agent
		
		
		
		
		
	
