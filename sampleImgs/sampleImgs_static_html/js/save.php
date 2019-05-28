<?php 
$file = fopen("database.js", "w");
$txt = isset($_POST['db']) ? $_POST['db'] : null;
$txt = "roistore = " . $txt;
fwrite($file, $txt);
fclose($file);

?>