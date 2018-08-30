import base64
import json
import random
import re
import sys

tree = None
allNodes = None
roots = None
bestWeight = 0
bestConf = None
totalIterations = 0
memoizeMap = {}

nodeToClassMap = {
    47175: 1, # Marauder
    50459: 2, # Ranger
    54447: 3, # Witch
    50986: 4, # Duelist
    61525: 5, # Templar
    44683: 6, # SIX
    58833: 0, # Seven
}

def staticMemoize( function ):
    staticMemoize = {}
    def helper( arg, *argv ):
        if ( arg, *argv ) not in staticMemoize:
            staticMemoize[ ( arg, *argv ) ] = function( arg, *argv )
        return staticMemoize[ ( arg, *argv ) ]
    return helper

class Configuration( object ):
    def __init__( self, nodes=None ):
        self.job = None
        self.ascendancy = None
        self.head = None
        self.nodes = []
        self.weight = 0
        if nodes:
            self.nodes = nodes
            self.job = nodeToClassMap[ nodes[ 0 ] ]

    def setNodes( self, nodes ):
        self.nodes = nodes

    def addNode( self, node ):
        self.nodes.append( node )

    def getNodes( self ):
        return self.nodes

    def setJob( self, job ):
        self.job = job

    def getJob( self ):
        return self.job

def loadJson( fileName ):
    '''
        Loads the "nodes" dict from json file.
    '''
    treefile = open( fileName )
    jsontree = json.load( treefile )
    return jsontree

def setLinks( nodes ):
    '''
        Sets the link attributes for all nodes.
    '''
    for node in nodes:
        nodes[ node ][ 'link' ] = []
    for node in nodes:
        relatedNodes = nodes[ node ][ 'in' ] + nodes[ node ][ 'out' ]
        for relatedNode in relatedNodes:
            if relatedNode not in nodes[ node ][ 'link' ]:
                nodes[ node ][ 'link' ].append( relatedNode )
            if int( node ) not in nodes[ str( relatedNode ) ][ 'link' ]:
                nodes[ str( relatedNode ) ][ 'link' ].append( int( node ) )
    return nodes

def saveToUrl( conf ):
    print( 'Saving config to usable URL' )
    nodes = conf.getNodes()
    size = ( len( nodes ) - 1 ) * 2 + 7
    resBytes = bytearray( size )
    resBytes[ 0 ] = 0
    resBytes[ 1 ] = 0
    resBytes[ 2 ] = 0
    resBytes[ 3 ] = 4
    resBytes[ 4 ] = conf.getJob()
    resBytes[ 5 ] = 0
    resBytes[ 6 ] = 0
    pos = 7
    for node in nodes:
        if node in nodeToClassMap.keys():
            print( 'Found a class start node, ignoring...' )
            continue
        tempNode = node
        resBytes[ pos + 1 ] = tempNode & 0xFF
        tempNode >>= 8
        resBytes[ pos ] = tempNode & 0xFF
        pos += 2
    encoded = base64.b64encode( resBytes )
    encodedUrl = str( encoded ).replace( '/', '_' ).replace( '+', '-' )
    print( 'Result' )
    print( 'https://www.pathofexile.com/passive-skill-tree/3.4/' + encodedUrl.strip( "'" )[ 2: ] )

@staticMemoize
def maxStrength( node ):
    totalStrength = 0
    for text in allNodes[ str( node ) ].get( 'sd' ):
        if re.findall( 'Strength', text ) != []:
            try:
                match = re.match( r'\+(\d+)', text ).group( 0 )
            except:
                print( text )
                raise
            totalStrength += int( match )
    return totalStrength

def bruteForceGenerator( numPassives, weightFunc ):
    print( 'Generating a brute force absolute best tree with %s passive points for weight function %s.' % ( numPassives, weightFunc.__name__ ) )
    def checkConf( conf ):
        global memoizeMap
        global bestWeight
        global bestConf
        def getTotalWeight( nodes, weightFunc ):
            totalWeight = 0
            for node in nodes:
                totalWeight += weightFunc( node )
            return totalWeight
        nodes = sorted( conf.getNodes() )
        tupleNodes = tuple( nodes )
        confWeight = memoizeMap.get( tupleNodes )
        if confWeight == None:
            confWeight = getTotalWeight( nodes, weightFunc )
            memoizeMap[ tupleNodes ] = confWeight
        if confWeight > bestWeight:
            bestWeight = confWeight
            bestConf = conf
    def recursive( conf, unchosens ):
        #print( 'Entering recursion with %s nodes and %s unchosen nodes.' % ( len( conf.getNodes() ), len( unchosens ) ) )
        global totalIterations
        totalIterations += 1
        checkConf( conf )
        nodes = conf.getNodes()
        if len( nodes ) >= numPassives + 1:
            return
        for unchosen in unchosens:
            if unchosen not in nodes:
                newUnchosens = [ node for node in allNodes[ str( unchosen ) ][ 'link' ]
                                 if not allNodes[ str( node ) ].get( 'isAscendancyStart' )
                                 and allNodes[ str( node ) ].get( 'ascendancyName' ) != 'Ascendant'
                                 and node not in unchosens
                                 and node not in nodes ] + unchosens
                newUnchosens.remove( unchosen )
                recursive( Configuration( nodes + [ unchosen ] ), newUnchosens )
    for job in nodeToClassMap:
        conf = Configuration( [ job ] )
        unchosens = [ node for node in allNodes[ str( job ) ][ 'link' ]
                      if not allNodes[ str( node ) ].get( 'isAscendancyStart' )
                      and allNodes[ str( node ) ].get( 'ascendancyName' ) != 'Ascendant'
                      and node != job ]
        recursive( conf, unchosens )
    print( 'Final result is weight %s.' % bestWeight )
    print( 'Took %s iterations.' % totalIterations )
    return bestConf

def randomTreeGenerator( numPassives=123 ):
    print( 'Generating a random configuration of %s passive points' % numPassives )
    randomConf = Configuration()
    startNode = random.choice( roots )
    randomConf.setJob( nodeToClassMap[ startNode ] )
    randomConf.addNode( startNode )
    unchosenNodes = []
    for startNodeOut in allNodes[ str( startNode ) ][ 'link' ]:
        if not allNodes[ str( startNodeOut ) ].get( 'isAscendancyStart' ) and startNodeOut not in unchosenNodes and startNodeOut not in randomConf.getNodes():
            unchosenNodes.append( startNodeOut )
    for iteration in range( numPassives ):
        chosenNode = random.choice( unchosenNodes )
        unchosenNodes.remove( chosenNode )
        randomConf.addNode( chosenNode )
        for chosenNodeOut in allNodes[ str( chosenNode ) ][ 'link' ]:
            if not allNodes[ str( chosenNodeOut ) ].get( 'isAscendancyStart' ) and \
               chosenNodeOut not in unchosenNodes and \
               chosenNodeOut not in randomConf.getNodes() and \
               allNodes[ str( chosenNodeOut ) ].get( 'ascendancyName' ) != 'Ascendant':
                unchosenNodes.append( chosenNodeOut )
            else:
                iteration -= 1
        if unchosenNodes == []:
            print( 'Ended prematurely at iteration %s' % iteration )
            break
    return randomConf
            
def run():
    global tree
    global allNodes
    global roots
    tree = loadJson( 'C:\\Users\\Zhi Yuan Zhao\\Desktop\\data.txt' )
    allNodes = setLinks( tree[ 'nodes' ] )
    roots = tree[ 'root' ][ 'out' ]
    if len( sys.argv ) > 1:
        print( allNodes[ sys.argv[1] ] )
        sys.exit( 0 )
    testConf = randomTreeGenerator()
    testNodes = testConf.getNodes()
    print( testConf.getNodes() )

    saveToUrl( testConf )

if __name__ == '__main__':
    run()
