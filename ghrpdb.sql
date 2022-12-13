-- phpMyAdmin SQL Dump
-- version 5.2.0
-- https://www.phpmyadmin.net/
--
-- Host: 127.0.0.1
-- Generation Time: Oct 13, 2022 at 08:35 AM
-- Server version: 10.6.10-MariaDB-log
-- PHP Version: 7.4.32

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Database: `ghrpdb`
--

-- --------------------------------------------------------

--
-- Table structure for table `cn_boost_patch`
--

CREATE TABLE `cn_boost_patch` (
  `repo_id` int(11) NOT NULL,
  `cn_url` text DEFAULT NULL,
  `cn_url_beta` text DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- --------------------------------------------------------

--
-- Table structure for table `patch_history`
--

CREATE TABLE `patch_history` (
  `id` int(11) NOT NULL,
  `repo_id` int(11) NOT NULL,
  `publish_time` datetime NOT NULL,
  `tag_name` text NOT NULL,
  `body` text NOT NULL,
  `download_url` text NOT NULL,
  `is_prerelease` int(1) NOT NULL COMMENT '0 for False;1 for True'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- --------------------------------------------------------

--
-- Table structure for table `repo_list`
--

CREATE TABLE `repo_list` (
  `id` int(11) NOT NULL,
  `repo_name` text NOT NULL,
  `friendly_name` text NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- --------------------------------------------------------

--
-- Table structure for table `token`
--

CREATE TABLE `token` (
  `Id` int(11) NOT NULL,
  `value` varchar(64) NOT NULL,
  `user_id` int(11) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- --------------------------------------------------------

--
-- Table structure for table `user`
--

CREATE TABLE `user` (
  `id` int(16) NOT NULL,
  `username` varchar(255) NOT NULL,
  `password` varchar(255) NOT NULL COMMENT 'hashed password',
  `email` varchar(255) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

--
-- Indexes for dumped tables
--

--
-- Indexes for table `cn_boost_patch`
--
ALTER TABLE `cn_boost_patch`
  ADD KEY `repo_list_id_to_cn_list` (`repo_id`);

--
-- Indexes for table `patch_history`
--
ALTER TABLE `patch_history`
  ADD PRIMARY KEY (`id`),
  ADD KEY `repo_id_to_patch` (`repo_id`);

--
-- Indexes for table `repo_list`
--
ALTER TABLE `repo_list`
  ADD PRIMARY KEY (`id`);

--
-- Indexes for table `token`
--
ALTER TABLE `token`
  ADD PRIMARY KEY (`Id`),
  ADD KEY `token_user_id` (`user_id`);

--
-- Indexes for table `user`
--
ALTER TABLE `user`
  ADD PRIMARY KEY (`id`);

--
-- AUTO_INCREMENT for dumped tables
--

--
-- AUTO_INCREMENT for table `patch_history`
--
ALTER TABLE `patch_history`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `repo_list`
--
ALTER TABLE `repo_list`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `token`
--
ALTER TABLE `token`
  MODIFY `Id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `user`
--
ALTER TABLE `user`
  MODIFY `id` int(16) NOT NULL AUTO_INCREMENT;

--
-- Constraints for dumped tables
--

--
-- Constraints for table `cn_boost_patch`
--
ALTER TABLE `cn_boost_patch`
  ADD CONSTRAINT `repo_list_id_to_cn_list` FOREIGN KEY (`repo_id`) REFERENCES `repo_list` (`id`);

--
-- Constraints for table `patch_history`
--
ALTER TABLE `patch_history`
  ADD CONSTRAINT `repo_id_to_patch` FOREIGN KEY (`repo_id`) REFERENCES `repo_list` (`id`) ON DELETE CASCADE ON UPDATE CASCADE;

--
-- Constraints for table `token`
--
ALTER TABLE `token`
  ADD CONSTRAINT `token_user_id` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`);
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
