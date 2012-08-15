#!/usr/bin/env php
<?php
$root = dirname(dirname(dirname(__FILE__)));
require_once $root.'/scripts/__init_script__.php';

$args = new PhutilArgumentParser($argv);
$args->setTagline('generate interfaces.json for Python Phabricator client');
$args->setSynopsis(<<<EOHELP
**gen_api_interfaces.php** ...
  Generate interfaces.json for Python Phabricator client
EOHELP
);
$args->parseStandardArguments();
$args->parse(
  array(
  ));

$console = PhutilConsole::getConsole();

function map_param_type($param_type) {
    $ex_param_type = explode('<', $param_type, 2);
    switch ($ex_param_type[0]) {
        case 'int':
        case 'uint':
        case 'revisionid':
        case 'revision_id':
        case 'diffid':
        case 'diff_id':
        case 'id':
        case 'enum':
            return 'int';
        case 'bool':
            return 'bool';
        case 'dict':
            return 'dict';
        case 'list':
            if (!isset($ex_param_type[1]) || !preg_match('/([[:alpha:]]+).*/', $ex_param_type[1], $matches)) {
                return array('str');
            }
            return array(map_param_type($matches[1]));
        case 'string':
        case 'phid':
        default:
            return 'str';
    }
}

$classes = id(new PhutilSymbolLoader())
      ->setAncestorClass('ConduitAPIMethod')
      ->setType('class')
      ->setConcreteOnly(true)
      ->selectSymbolsWithoutLoading();
$klasses = array_values(ipull($classes, 'name'));

$the_map = array();
foreach ($klasses as $method_class) {
  $method_name = ConduitAPIMethod::getAPIMethodNameFromClassName($method_class);
  $method_object = newv($method_class, array());

  $status = $method_object->getMethodStatus();
  # TODO: Filter on $status

  $group_name = head(explode('.', $method_name));
  if (!array_key_exists($group_name, $the_map)) {
    $the_map[$group_name] = array();
  }
  $map_group = &$the_map[$group_name];

  $map_group[last(explode('.', $method_name))] = array(
    'required' => array(),
    'optional' => array(),
    'method'   => 'POST',
    'formats'  => array('json', 'human'));
  $map_method = &$map_group[last(explode('.', $method_name))];

  $params = $method_object->defineParamTypes();
  foreach ($params as $param_name => $param_desc) {
    $ex_param_desc = explode(' ', $param_desc);
    $param_optionality = head($ex_param_desc);

    $map_method[$param_optionality][$param_name] = map_param_type($ex_param_desc[1]);
  }
  ksort($map_method['required']);
  ksort($map_method['optional']);
}

ksort($the_map);
foreach ($the_map as $group_name => &$group) {
  ksort($group);
}

$console->writeOut(json_encode($the_map));
exit(0);
