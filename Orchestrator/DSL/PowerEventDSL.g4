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
  : functionDef
  | clusterDef
  | eventDef
  ;

functionDef
  : 'func' IDENTIFIER '(' functionParamList? ')' '{' (clusterDef | eventDef)* '}'
  ;

clusterDef
  : 'def' gridElementType 'cluster' clusterId clusterDefinition ';'
  | 'def' dynamicModelLibAtom 'cluster' clusterId dynamicModelClusterDefinition ';'
  ;

functionParamList
  : IDENTIFIER (',' IDENTIFIER)*
  ;

// Events
eventDef
  : timeAnchor intervalSpec ',' rampableAction (tagged)? ';'
  | (timeAnchor timeExpr ',')? executable (tagged)? ';'
  | triggeredStatement
  ;

// 'at' is an absolute simulation time, 'after' is relative (to the script parsing time, or to the containing function call time)
timeAnchor
  : 'at'
  | 'after'
  ;

rampableAction
  : adjustGridAction
  | rampSetGridAction
  ;

triggeredStatement
  : 'when' dynamicExpression ',' executable (tagged)? ';'
  // Like 'when', but rearms itself once the condition becomes false again, so it can re-fire
  | 'when_rearming' dynamicExpression ',' executable (tagged)? ';'
  | 'after' tag 'is' 'completed' ',' executable (tagged)? ';'
  ;

tagged
  : 'tagged' tag
  ;

tag
  : stringAtom
  ;

executable
  : pointAction
  | callExpr
  | validateExpr
  ;

callExpr
  : IDENTIFIER '(' callArgList? ')'
  ;

// Validates that a function call would succeed (all sub-events resolve against the current
// network/scope) without actually applying any of its effects; reports an error if it wouldn't.
validateExpr
  : 'validate' '(' callExpr ')'
  ;

callArgList
  : callArg (',' callArg)*
  ;

callArg
  : (IDENTIFIER ':')? callArgValue
  ;

callArgValue
  : timeValue
  | varRef  // Before the atoms so that they don't pin a bare '$x' to their own type.
  | signedNumericAtom
  | booleanAtom
  | STRING
  ;

// Actions
pointAction
  : switchAction
  | lineAction
  | transformerAction
  | adjustGridAction
  | setGridAction
  | networkAction
  ;

switchAction
  : ('open' | 'close') 'switch' switchId
  ;
switchId
  : stringAtom
  ;
lineAction
  : ('open' | 'close') 'line' lineId
  ;
lineId
  : stringAtom
  ;
// Works on both 2_windings_transformer and 3_windings_transformer
transformerAction
  : ('open' | 'close') 'transformer' transformerId
  ;
transformerId
  : stringAtom
  ;
adjustGridAction
  : ('increase' | 'decrease') target 'input' inputType 'by' numericAtom PERCENT
  ;
setGridAction
  : 'set' target 'input' inputType 'to' signedNumber
  ;
rampSetGridAction
  : 'set' target 'input' inputType ('from' signedNumber)? 'to' signedNumber
  ;
inputType
  : stringAtom
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
  : 'link' 'from' nodeId 'to' nodeId
  ;

nodeClause
  : 'node' nodeId
  ;

nodeId
  : stringAtom
  ;

delayClause
  : 'delay' delayFunction
  ;

delayFunction
  : 'fixed' numericAtom timeUnit
  | 'gauss' 'mean' numericAtom timeUnit 'stddev' numericAtom timeUnit
  ;

dropClause
  : 'drop' dropFunction
  ;

dropFunction
  : 'fixed' booleanAtom
  | 'random' numericAtom
  ;

corruptionClause
  : 'corruption' corruptionFunction
  ;

corruptionFunction
  : 'none' (likelihoodClause)?
  | 'random_noise_measurement' corruptionNoiseParams
  | 'random_noise_control' corruptionNoiseParams
  | 'zero_out_measurement' corruptionZeroParams
  | 'shift_measurement' corruptionShiftParams
  | 'invert_control' corruptionInvertParams
  ;

likelihoodClause
  : 'likelihood' numericAtom
  ;

corruptionNoiseParams
  : (likelihoodClause)? 'range' numericAtom 'to' numericAtom
  ;

corruptionZeroParams
  : (likelihoodClause)? ('value' numericAtom)?
  ;

corruptionShiftParams
  : (likelihoodClause)? 'by' numericAtom
  ;

corruptionInvertParams
  : (likelihoodClause)? ('by' numericAtom)?
  ;

// IIDM element types (Pypowsybl nomenclature)
gridElementType
  : '2_windings_transformer'
  | '3_windings_transformer'
  // | 'alias'  // Don't consider element that cannot be controlled / that are non-physical to limit noise (e.g. in autocomplete)
  // | 'area'
  | 'battery'
  // | 'branch'
  // | 'busbar_section'
  // | 'bus'
  // | 'bus_breaker_view_bus'
  | 'dangling_line'
  | 'generator'
  | 'hvdc_line'
  // | 'identifiable'
  // | 'injection'
  | 'lcc_converter_station'
  | 'line'
  | 'load'
  // | 'linear_shunt_compensator_section'
  // | 'non_linear_shunt_compensator_section'
  // | 'operational_limit'
  | 'phase_tap_changer'
  | 'ratio_tap_changer'
  | 'shunt_compensator'
  | 'static_var_compensator'
  | 'substation'
  | 'switch'
  | 'voltage_level'
  | 'vsc_converter_station'
  | 'tie_line'
  ;

target
  : gridElementType gridElementId
  | gridElementType gridElementList
  | clusterSpec
  | dynamicModelTarget
  ;

// Purely dynamic Dynawo model, similar to IIDM, but keyed by 'lib' 'model_id' instead of line 'iidm_id
dynamicModelTarget
  : dynamicModelLibAtom dynamicModelAtom
  | dynamicModelLibAtom dynamicModelList
  | dynamicModelClusterSpec
  ;
dynamicModelList
  : '[' dynamicModelAtom (',' dynamicModelAtom)* ']'
  ;
dynamicModelClusterSpec
  : dynamicModelLibAtom 'cluster' clusterId (dynamicModelClusterDefinition)?
  | dynamicModelLibAtom 'cluster' dynamicModelClusterDefinition
  ;
dynamicModelClusterDefinition
  : dynamicModelList
  | dynamicModelRegexFilter
  ;
dynamicModelRegexFilter
  : 'regex' stringAtom 'on' dynamicModelLibAtom
  ;
dynamicModelLibAtom
  : stringAtom
  ;
dynamicModelAtom
  : stringAtom
  ;
gridElementId
  : stringAtom
  ;
gridElementList
  : '[' gridElementId (',' gridElementId)* ']'
  ;

clusterSpec
  : gridElementType 'cluster' clusterId (clusterDefinition)?
  | gridElementType 'cluster' clusterDefinition
  ;
clusterId
  : stringAtom
  ;
clusterDefinition
  : gridElementList
  | relationshipSpec
  ;

signedNumber
  : signedNumericAtom
  ;

signedNumericAtom
  : ('+' | '-')? numericAtom
  ;

stringAtom
  : STRING
  | varRef
  ;

numericAtom
  : NUMBER
  | varRef
  ;

booleanAtom
  : booleanLiteral
  | varRef
  ;

// Reference to a function parameter's value
varRef
  : '$' IDENTIFIER
  ;

// Relationship filters
relationshipSpec
  : regexFilter
  /* | groupByFilter  // Temporarily removed (non-obvious implementation)
  | propertyFilter */
  ;
regexFilter
  : 'regex' stringAtom 'on' gridElementType
  ;
/* Temporarily removed (non-obvious implementation)
groupByFilter
  : 'group' 'by' propertyName stringAtom 'on' gridElementType
  ;
propertyFilter
  : 'where' propertyName comparison numericAtom 'on' gridElementType
  ;
propertyName
  : stringAtom
  ;
*/

// Timing
timeValue
  : numericAtom timeUnit
  ;
timeUnit
  : 'seconds'
  | 'second'
  | 's'
  | 'minutes'
  | 'minute'
  | 'min'
  | 'hours'
  | 'hour'
  | 'h'
  ;

timeExpr
  : timeValue
  | varRef
  ;
intervalSpec
  : '[' timeExpr ',' timeExpr ']' ('with' 'law' lawSpec)?
  ;
// Each supported law is added here explicitly as it's implemented
lawSpec
  : 'linear'
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
  : ('+' | '-')? ( numericAtom | variable | '(' arithmeticExpr ')' )
  ;
comparison
  : '<' | '>' | '<=' | '>=' | '==' | '!='
  ;
booleanLiteral
  : 'true' | 'false'
  ;

variable
  : gridElementType gridElementId 'output' outputType
  | dynamicModelLibAtom dynamicModelAtom 'output' outputType
  ;
outputType
  : stringAtom
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
// Any continuous unquoted string, except reserved keywords (every literal token used above, e.g. 'line', 'load', 'true'...), which always take
// priority over this rule (as they are declared sooner) and can therefore never be used as a function or parameter name.
IDENTIFIER
  : [a-zA-Z_] [a-zA-Z0-9_]*
  ;

WS
  : [ \t\r\n]+ -> skip
  ;
COMMENT
  : '//' ~[\r\n]* -> skip
  ;
