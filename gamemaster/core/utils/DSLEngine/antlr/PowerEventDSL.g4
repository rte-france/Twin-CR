/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

grammar PowerEventDSL;

// Top-level
program
  : statement* EOF
  ;

// Statements
statement
  : setDuration
  | setTimeStep
  | functionDef
  | eventDef
  ;

functionDef
  : 'func' IDENTIFIER '(' functionParamList? ')' '{' functionStatement* '}'
  ;

functionParamList
  : IDENTIFIER (',' IDENTIFIER)*
  ;

// Setters
setDuration
  : 'set' 'simulation' 'duration' 'to' timeValue ';'
  ;
setTimeStep
  : 'set' 'time' 'step' 'to' timeValue ';'
  ;

// Events
eventDef
  : ('at' timeSpec ',')? executable (tagged)? ';'
  | 'when' dynamicExpression ',' executable (tagged)? ';'
  | 'after' stringAtom 'is' 'completed' ',' executable (tagged)? ';'
  ;

functionStatement
  : 'at' relativeTimeSpec ',' executable (tagged)? ';'
  | 'when' dynamicExpression ',' executable (tagged)? ';'
  | 'after' stringAtom 'is' 'completed' ',' executable (tagged)? ';'
  ;

tagged
  : 'tagged' stringAtom
  ;

executable
  : action
  | callExpr
  | verifiedCallExpr
  ;

callExpr
  : IDENTIFIER '(' callArgList? ')'
  ;

verifiedCallExpr
  : 'checkAndApply' '(' callExpr ')'
  ;

callArgList
  : callArg (',' callArg)*
  ;

callArg
  : (IDENTIFIER ':')? callArgValue
  ;

callArgValue
  : target
  | timeValue
  | signedNumericAtom
  | booleanLiteral
  ;

// Actions
action
  : switchAction
  | lineAction
  | loadAction
  | genAction
  | setLoadAction
  | setGenAction
  | faultAction
  | clearFaultAction
  | networkAction
  | printAction
  ;

printAction
  : 'print' STRING
  ;

switchAction
  : ('open' | 'close') 'switch' stringAtom
  ;
lineAction
  : ('open' | 'close') 'line' stringAtom
  ;
loadAction
  : ('increase' | 'decrease') 'load' target 'by' numericAtom PERCENT (channelSpec)?
  ;
genAction
  : ('increase' | 'decrease') 'generator' target 'by' numericAtom PERCENT (channelSpec)?
  ;
setLoadAction
  : 'set' 'load' target setRange (channelSpec)?
  ;
setGenAction
  : 'set' 'generator' target setRange (channelSpec)?
  ;
faultAction
  : 'apply' 'fault' 'at' component
  ;
clearFaultAction
  : 'clear' 'fault' 'at' component
  ;
networkAction
  : 'change' 'network' 'characteristics'
    (linkStatement (',' nodeStatement)? | nodeStatement)
    (',' networkAdjustmentClause)*
  ;

linkStatement
  : linkClause (',' linkClause)*
  ;

nodeStatement
  : nodeClause (',' nodeClause)*
  ;

networkAdjustmentClause
  : delayClause
  | dropClause
  | corruptionClause
  ;

linkClause
  : 'link' 'from' STRING 'to' STRING
  ;

nodeClause
  : 'node' STRING
  ;

delayClause
  : 'delay' delayFunction
  ;

delayFunction
  : 'fixed' NUMBER timeUnit
  | 'gauss' 'mean' NUMBER timeUnit 'stddev' NUMBER timeUnit
  ;

dropClause
  : 'drop' dropFunction
  ;

dropFunction
  : 'fixed' booleanLiteral
  | 'random' NUMBER
  ;

corruptionClause
  : 'corruption' corruptionFunction
  ;

corruptionFunction
  : 'none' ('likelihood' NUMBER)?
  | 'random_noise_measurement' corruptionNoiseParams
  | 'random_noise_control' corruptionNoiseParams
  | 'zero_out_measurement' corruptionZeroParams
  | 'shift_measurement' corruptionShiftParams
  | 'invert_control' corruptionInvertParams
  ;

corruptionNoiseParams
  : ('likelihood' NUMBER)? 'range' NUMBER 'to' NUMBER
  ;

corruptionZeroParams
  : ('likelihood' NUMBER)? ('value' NUMBER)?
  ;

corruptionShiftParams
  : ('likelihood' NUMBER)? 'by' NUMBER
  ;

corruptionInvertParams
  : ('likelihood' NUMBER)? ('by' NUMBER)?
  ;

// Components and targets
component
  : componentType stringAtom
  ;
componentType
  : 'line'
  | 'generator'
  | 'twoWindingsTransformer'
  | 'threeWindingsTransformer'
  | 'substation'
  | 'voltageLevel'
  | 'busbarSection'
  | 'switch'
  | 'load'
  | 'battery'
  | 'shunt'
  | 'staticVarCompensator'
  | 'hvdcLine'
  | 'bus'
  | 'asset'
  | '2_windings_transformer'
  | '3_windings_transformer'
  ;

target
  : stringAtom
  | listSpec
  | clusterSpec
  | dynamicClusterSpec
  ;
listSpec
  : '[' listItem (',' listItem)* ']'
  ;
listItem
  : stringAtom
  ;

clusterSpec
  : 'cluster' (stringAtom)? listSpec
  ;
dynamicClusterSpec
  : 'dynamic' 'cluster' relationshipSpec
  ;

channelSpec
  : 'P'
  | 'Q'
  | 'U'
  | 'state'
  ;

setRange
  : ('from' signedNumber)? 'to' signedNumber
  ;

signedNumber
  : signedNumericAtom
  ;

signedNumericAtom
  : ('+' | '-')? numericAtom
  ;

stringAtom
  : STRING
  | IDENTIFIER
  ;

numericAtom
  : NUMBER
  | IDENTIFIER
  ;

// Relationship filters
relationshipSpec
  : regexFilter
  | groupByFilter
  | propertyFilter
  ;
regexFilter
  : 'regex' stringAtom 'on' componentType
  ;
groupByFilter
  : 'group' 'by' propertyName stringAtom 'on' componentType
  ;
propertyFilter
  : 'where' propertyName comparison numericAtom (unit)? 'on' componentType
  ;
propertyName
  : stringAtom
  ;

// Timing
timeValue
  : numericAtom timeUnit
  ;
timeUnit
  : 'seconds'
  | 'second'
  | 'minutes'
  | 'minute'
  | 'hours'
  | 'hour'
  ;

timeSpec
  : timeExpr
  | intervalSpec
  ;
timeExpr
  : timeValue
  | nowExpr
  | IDENTIFIER
  ;
nowExpr
  : 'now' (('+'|'-') timeValue)?
  ;
intervalSpec
  : '[' timeExpr ',' timeExpr ']' ('with' 'law' lawSpec)?
  ;
relativeTimeSpec
  : relativeTimeExpr
  | relativeIntervalSpec
  ;
relativeTimeExpr
  : relativeTimeValue
  | IDENTIFIER
  ;
relativeTimeValue
  : signedNumericAtom timeUnit
  ;
relativeIntervalSpec
  : '[' relativeTimeExpr ',' relativeTimeExpr ']' ('with' 'law' lawSpec)?
  ;
lawSpec
  : STRING
  | 'linear'
  ;

// Dynamic expressions
dynamicExpression
  : expression
  ;
expression
  : booleanExpr
  ;
booleanExpr
  : booleanTerm ('or' booleanTerm)*
  ;
booleanTerm
  : booleanFactor ('and' booleanFactor)*
  ;
booleanFactor
  : booleanAtomic
  | '(' booleanExpr ')'
  ;
booleanAtomic
  : comparisonExpr
  | booleanLiteral
  ;
comparisonExpr
  : arithmeticExpr comparison arithmeticExpr
  ;
arithmeticExpr
  : term (('+'|'-') term)*
  ;
term
  : factor (('*'|'/') factor)*
  ;
factor
  : numberWithUnit
  | variable
  | '(' arithmeticExpr ')'
  ;
numberWithUnit
  : numericAtom (unit)?
  ;
comparison
  : '<' | '>' | '<=' | '>=' | '==' | '!='
  ;
booleanLiteral
  : 'true' | 'false'
  ;

variable
  : 'voltage' 'at' 'voltageLevel' stringAtom
  | 'frequency' 'at' 'voltageLevel' stringAtom
  | 'power' 'flow' 'on' 'line' stringAtom
  | 'active_flow' 'on' 'line' stringAtom
  | 'reactive_flow' 'on' 'line' stringAtom
  ;

// Units
unit
  : 'pu' | 'Hz' | 'MW' | 'MVar' | 'kV'
  ;

// Lexer rules
NUMBER
  : [0-9]+ ('.' [0-9]+)?
  ;
PERCENT
  : '%'
  ;
STRING
  : '"' ( ~["\r\n] )* '"'   // anything but quote or newline
  ;
IDENTIFIER
  : [a-zA-Z_] [a-zA-Z0-9_]*
  ;

WS
  : [ \t\r\n]+ -> skip
  ;
COMMENT
  : '//' ~[\r\n]* -> skip
  ;
