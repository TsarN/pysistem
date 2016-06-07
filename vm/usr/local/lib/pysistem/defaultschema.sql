DROP DATABASE IF EXISTS pysistem;
CREATE DATABASE pysistem DEFAULT CHARACTER SET utf8 DEFAULT COLLATE utf8_general_ci;
GRANT ALL PRIVILEGES ON pysistem.* TO 'pysistem'@'localhost';
USE pysistem;

DROP TABLE IF EXISTS `compiler`;
CREATE TABLE `compiler` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(80) DEFAULT NULL,
  `lang` varchar(80) DEFAULT NULL,
  `cmd_compile` varchar(8192) DEFAULT NULL,
  `cmd_run` varchar(8192) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=9 DEFAULT CHARSET=utf8;
LOCK TABLES `compiler` WRITE;
INSERT INTO `compiler` VALUES (1,'GCC 5.3.1 - C99','c','gcc -Wall --std=c99 -O2 %src% -o %exe%','%exe%'),(2,'GCC 5.3.1 - C11','c','gcc -Wall --std=c11 -O2 %src% -o %exe%','%exe%'),(3,'G++ 5.3.1 - C++98','c','g++ -Wall --std=c++98 -O2 %src% -o %exe%','%exe%'),(4,'G++ 5.3.1 - C++11','c','g++ -Wall --std=c++11 -O2 %src% -o %exe%','%exe%'),(5,'Perl 5.22.1','pl','','perl %exe%'),(6,'Free Pascal 3.0.0','pas','mkdir %src%_WORK && fpc %src% -FE%src%_WORK && cp %src%_WORK/`basename %src% .pas` %exe%; rm -r %src%_WORK','%exe%');
UNLOCK TABLES;

DROP TABLE IF EXISTS `user`;
CREATE TABLE `user` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `username` varchar(40) DEFAULT NULL,
  `password` varchar(64) DEFAULT NULL,
  `first_name` varchar(32) DEFAULT NULL,
  `last_name` varchar(32) DEFAULT NULL,
  `email` varchar(32) DEFAULT NULL,
  `role` varchar(8) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `username` (`username`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8;

LOCK TABLES `user` WRITE;
INSERT INTO `user` VALUES (1,'Admin','__SIGNED_ADMIN_PASSWORD__',NULL,NULL,NULL,'admin');
UNLOCK TABLES;
