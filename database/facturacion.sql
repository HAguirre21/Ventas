-- phpMyAdmin SQL Dump
-- version 5.2.3
-- https://www.phpmyadmin.net/
--
-- Host: localhost:3306
-- Generation Time: Sep 18, 2026 at 10:28 PM
-- Server version: 8.4.3
-- PHP Version: 8.3.33

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Database: `facturacion`
--

-- --------------------------------------------------------

--
-- Table structure for table `productos`
--

CREATE TABLE `productos` (
  `id` int NOT NULL,
  `concepto` varchar(50) NOT NULL,
  `precio` int NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `productos`
--

INSERT INTO `productos` (`id`, `concepto`, `precio`) VALUES
(1, 'goma togo x 60', 8200),
(2, 'chicle tattoo x 100', 16500),
(3, 'patineta x 30', 16500),
(4, 'la picero x 30', 22000),
(5, 'cepillos dulces', 22000),
(6, 'huevo tibio x 24', 16700),
(7, 'huevo Frito x 12', 13600),
(8, 'paleta tajin x 12', 9000),
(9, 'paleta x 12 pimienta', 9000),
(10, 'paleta x 12 limon', 9000),
(11, 'mallas x 15', 7200),
(12, 'chupo x 30', 5600),
(13, 'pitillos x 30', 9800),
(14, 'jeringa Dulce x 30', 22000),
(15, 'coco tarro x 100', 8700),
(16, 'piñata kilo', 15500),
(17, 'fruty gumy candi x 12', 14700),
(18, 'goma Cinta x 30', 9000),
(19, 'bb x 55', 6500),
(20, 'tropi jelly x 20', 8000),
(21, 'crazy x 100', 6500),
(22, 'taco leche', 6500),
(23, 'yupi queso x 12', 12300),
(24, 'yupi caramelo x 12', 12300),
(25, 'yupi pollo x 12', 10300),
(26, 'yupi picante x 12', 10300),
(27, 'yupi natural x 12', 10300),
(28, 'picada shis x 12', 17900),
(29, 'cereales x 12', 9300),
(30, 'masmelo x 50', 6800),
(31, 'Mani x 20 pequeño', 5000),
(32, 'Mani x 20 grande', 12000),
(33, 'almendras x 100', 6500),
(34, 'anis tarro x 100', 6500),
(35, 'gaseosa sip  litro x 12', 21600),
(36, 'gaseosa sip 400 x 24', 21600),
(37, 'gaseosa sip 250 x 24', 17800),
(38, 'jugo sip 250 x 12', 9000),
(39, 'sip caja x 24', 12600),
(40, 'nutiva x 24', 14600),
(41, 'Rulas surtida x 12', 8000),
(42, 'Rulas mayonesa x 12', 8000),
(43, 'Rulas hotchile x 12', 8000),
(44, 'Rulas pollo x 12', 8000),
(45, 'Rulas limon x 12', 8000),
(46, 'nacho hot x 12', 7200),
(47, 'nacho blue x 12', 7200),
(48, 'kikecito queso x 12', 7200),
(49, 'kikecito hot x 12', 7200),
(50, 'crokantiras x 12', 7200),
(51, 'palitroques hot x 12', 7200),
(52, 'palitroques queso x 12', 7200),
(53, 'palitroques limon x 12', 7200),
(54, 'torniquetes hot x 12', 7200),
(55, 'rulizzz x 17', 18900),
(56, 'mini almuerzo x 24', 6000),
(57, 'boliqueso x 24', 5800),
(58, 'papa x 24', 5400),
(59, 'toston hot', 8000),
(60, 'toston Verde  limon', 8000),
(61, 'papa x 24 deli papa', 5000),
(62, 'papos x 12', 6300),
(63, 'deli papa x 12', 9500),
(64, 'rosquillas  limon x 30', 5300),
(65, 'rosquillas pollo x 30', 5300),
(66, 'palitos x 80', 4800),
(67, 'super palote x 80', 6000),
(68, 'bola sabores x 100', 6500),
(69, 'Maduro x 12', 12000),
(70, 'Maduro x 24', 6200),
(71, 'picada x 24', 5500),
(72, 'jaleas x 28', 6000),
(73, 'caleñas x 12', 11000),
(74, 'lenguas x 20', 7200),
(75, 'roscas x 60', 7800),
(76, 'galletas pepas x 60', 8000),
(77, 'peras x 20', 9500),
(78, 'torta pan Valle x 17', 13500),
(79, 'mantecada x 15', 14000),
(80, 'cuca x 12', 4600),
(81, 'galletas x 12', 4600),
(82, 'cuca manteca x 12', 4600),
(83, 'tostados pan Valle x 12', 17000),
(84, 'bocadillo combinao x 60', 23500),
(85, 'bocadillo guayaba x 60', 23500),
(86, 'vaso x 30', 9000),
(87, 'panelas leche x 50', 5700),
(88, 'panelas coco x 50', 5700),
(89, 'dona arequipe x 50', 6800),
(90, 'empanadas arequipe x 50', 6800),
(91, 'super chavo x 12', 11000),
(92, 'mini chavo x 12', 7800),
(93, 'sicodelica x 24', 6800),
(94, 'tornado x 24', 6800),
(95, 'satellite x 24', 6800),
(96, 'paleta corazon x 12', 6800),
(97, 'paleta labios rojos x 40', 16000),
(98, 'papa chipote x 12', 13000),
(99, 'papa jalapeña x 12', 13000),
(100, 'paleta UFO', 13000),
(101, 'polvo mix x 40', 5500),
(102, 'manjar x24', 5700),
(103, 'Agua con Gaz x20', 14000),
(104, 'sorpresa x70', 8300),
(105, 'polvorosa x60', 4200),
(106, 'galleta XXL', 30000),
(107, 'gela frutas x20', 8500),
(108, 'anaconda x20', 8500),
(109, 'gela x30', 5600),
(110, 'boloncho surtido x30', 9200),
(111, 'boloncho Rojo x30', 9200),
(112, 'boloncho mmago x30', 10000),
(113, 'bola surtida x60', 8500),
(114, 'bola rokax 60', 8500),
(115, 'bola Azul x60', 8500),
(116, 'bola mango x60', 8800),
(117, 'bola Sandia x60', 8800),
(118, 'carrots x20', 6500),
(119, 'celular x20', 6500),
(120, 'candy', 8200),
(121, 'cupi woo', 7800),
(122, 'chupi good', 8500),
(123, 'mas gum x60', 7200),
(124, 'paleta corazon x30', 8800),
(125, 'botellita acida x10', 7500),
(126, 'polvo sal. y limon', 7000);

-- --------------------------------------------------------

--
-- Table structure for table `productos_costa`
--

CREATE TABLE `productos_costa` (
  `id` int NOT NULL,
  `concepto` varchar(50) COLLATE utf8mb4_general_ci NOT NULL,
  `precio` int NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `productos_costa`
--

INSERT INTO `productos_costa` (`id`, `concepto`, `precio`) VALUES
(1, 'goma togo x 60', 8400),
(2, 'chicle tattoo x 100', 17000),
(3, 'patineta x 30', 17000),
(4, 'la picero x 30', 23000),
(5, 'cepillos dulces', 23000),
(6, 'huevo tibio x 24', 17000),
(7, 'huevo Frito x 12', 14000),
(8, 'paleta tajin x 12', 9200),
(9, 'paleta x 12 pimienta', 9200),
(10, 'paleta x 12 limon', 9200),
(11, 'mallas x 15', 7500),
(12, 'chupo x 30', 5800),
(13, 'pitillos x 30', 10000),
(14, 'jeringa Dulce x 30', 23000),
(15, 'coco tarro x 100', 9000),
(16, 'piñata kilo', 16000),
(17, 'fruty gumy candi x 12', 15000),
(18, 'goma Cinta x 30', 9500),
(19, 'bb x 55', 6500),
(20, 'tropi jelly x 20', 8500),
(21, 'crazy x 100', 7000),
(22, 'taco leche', 7000),
(23, 'yupi queso x 12', 12500),
(24, 'yupi caramelo x 12', 12500),
(25, 'yupi pollo x 12', 10500),
(26, 'yupi picante x 12', 10500),
(27, 'yupi natural x 12', 10500),
(28, 'picada shis x 12', 18200),
(29, 'cereales x 12', 9300),
(30, 'masmelo x 50', 6800),
(31, 'Mani x 20 pequeño', 5200),
(32, 'Mani x 20 grande', 12000),
(33, 'almendras x 100', 6700),
(34, 'anis tarro x 100', 6700),
(35, 'gaseosa sip  litro x 12', 22600),
(36, 'gaseosa sip 400 x 24', 22600),
(37, 'gaseosa sip 250 x 24', 19000),
(38, 'jugo sip 250 x 12', 9200),
(39, 'sip caja x 24', 13000),
(40, 'nutiva x 24', 15500),
(41, 'Rulas surtida x 12', 8400),
(42, 'Rulas mayonesa x 12', 8400),
(43, 'Rulas hotchile x 12', 8400),
(44, 'Rulas pollo x 12', 8400),
(45, 'Rulas limon x 12', 8400),
(46, 'nacho hot x 12', 8000),
(47, 'nacho blue x 12', 8000),
(48, 'kikecito queso x 12', 7500),
(49, 'kikecito hot x 12', 7500),
(50, 'crokantiras x 12', 7500),
(51, 'palitroques hot x 12', 7500),
(52, 'palitroques queso x 12', 7500),
(53, 'palitroques limon x 12', 7500),
(54, 'torniquetes hot x 12', 7500),
(55, 'rulizzz x 17', 20000),
(56, 'mini almuerzo x 24', 6000),
(57, 'boliqueso x 24', 6000),
(58, 'papa x 24', 5800),
(59, 'toston hot', 9000),
(60, 'toston Verde  limon', 9000),
(61, 'papa x 24 deli papa', 5300),
(62, 'papos x 12', 6800),
(63, 'deli papa x 12', 9700),
(64, 'rosquillas  limon x 30', 5500),
(65, 'rosquillas pollo x 30', 5500),
(66, 'palitos x 80', 5000),
(67, 'super palote x 80', 6200),
(68, 'bola sabores x 100', 7000),
(69, 'Maduro x 12', 12500),
(70, 'Maduro x 24', 6500),
(71, 'picada x 24', 6000),
(72, 'jaleas x 28', 6200),
(73, 'caleñas x 12', 12000),
(74, 'lenguas x 20', 7500),
(75, 'roscas x 60', 8000),
(76, 'galletas pepas x 60', 8200),
(77, 'peras x 20', 10000),
(78, 'torta pan Valle x 17', 14000),
(79, 'mantecada x 15', 14500),
(80, 'cuca x 12', 5000),
(81, 'galletas x 12', 5000),
(82, 'cuca manteca x 12', 5000),
(83, 'tostados pan Valle x 12', 17500),
(84, 'bocadillo combinao x 60', 24000),
(85, 'bocadillo guayaba x 60', 24000),
(86, 'vaso x 30', 9200),
(87, 'panelas leche x 50', 6000),
(88, 'panelas coco x 50', 6000),
(89, 'dona arequipe x 50', 7000),
(90, 'empanadas arequipe x 50', 7000),
(91, 'super chavo x 12', 11500),
(92, 'mini chavo x 12', 8000),
(93, 'sicodelica x 24', 7000),
(94, 'tornado x 24', 7000),
(95, 'satellite x 24', 7000),
(96, 'paleta corazon x 12', 7000),
(97, 'paleta labios rojos x 40', 16500),
(98, 'papa chipote x 12', 13000),
(99, 'papa jalapeña x 12', 13000),
(100, 'paleta UFO', 13500),
(101, 'polvo mix x 40', 5500),
(102, 'manjar x24', 6000),
(103, 'Agua con Gaz x20', 15000),
(104, 'sorpresa x70', 8500),
(105, 'polvorosa x60', 4500),
(106, 'galleta XXL', 31000),
(107, 'gela frutas x20', 9000),
(108, 'anaconda x20', 9000),
(109, 'gela x30', 6000),
(110, 'boloncho surtido x30', 9500),
(111, 'boloncho Rojo x30', 9500),
(112, 'boloncho mmago x30', 10200),
(113, 'bola surtida x60', 8700),
(114, 'bola rokax 60', 8700),
(115, 'bola Azul x60', 8700),
(116, 'bola mango x60', 9000),
(117, 'bola Sandia x60', 9000),
(118, 'carrots x20', 6700),
(119, 'celular x20', 6700),
(120, 'candy', 8400),
(121, 'cupi woo', 8000),
(122, 'chupi good', 8700),
(123, 'mas gum x60', 7500),
(124, 'paleta corazon x30', 9000),
(125, 'botellita acida x10', 8000),
(126, 'polvo sal. y limon', 7500);

--
-- Indexes for dumped tables
--

--
-- Indexes for table `productos`
--
ALTER TABLE `productos`
  ADD PRIMARY KEY (`id`);

--
-- Indexes for table `productos_costa`
--
ALTER TABLE `productos_costa`
  ADD PRIMARY KEY (`id`);

--
-- AUTO_INCREMENT for dumped tables
--

--
-- AUTO_INCREMENT for table `productos`
--
ALTER TABLE `productos`
  MODIFY `id` int NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=127;

--
-- AUTO_INCREMENT for table `productos_costa`
--
ALTER TABLE `productos_costa`
  MODIFY `id` int NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=127;
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
