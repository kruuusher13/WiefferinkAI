-- Mock Database Schema for WinCar (MS SQL Server)
-- Created for GarageAI testing

-- Table: Klanten (Module: Communicatie)
CREATE TABLE Communicatie_Relaties (
    KlantID INT PRIMARY KEY IDENTITY(1,1),
    KlantNaam NVARCHAR(100) NOT NULL,
    Telefoon NVARCHAR(20),
    Email NVARCHAR(100),
    Adres NVARCHAR(200),
    Woonplaats NVARCHAR(100)
);

-- Table: Voertuigen (Module: Werkplaats/Verkoop)
CREATE TABLE Werkplaats_Voertuigen (
    VoertuigID INT PRIMARY KEY IDENTITY(1,1),
    Kenteken NVARCHAR(20) NOT NULL UNIQUE,
    MerkNee NVARCHAR(50),
    Model NVARCHAR(50),
    KlantID INT, -- Foreign key linking owner
    Bouwjaar INT,
    CONSTRAINT FK_Voertuig_Klant FOREIGN KEY (KlantID) REFERENCES Communicatie_Relaties(KlantID)
);

-- Table: Werkorders (Module: Werkplaats)
CREATE TABLE Werkplaats_Werkorders (
    WerkorderID INT PRIMARY KEY IDENTITY(2024000,1),
    VoertuigID INT NOT NULL,
    Status NVARCHAR(50) DEFAULT 'Gepland', -- In behandeling, Wacht op onderdelen, Klaar, Gefactureerd
    Omschrijving NVARCHAR(MAX),
    AanmaakDatum DATETIME DEFAULT GETDATE(),
    AfmeldDatum DATETIME,
    CONSTRAINT FK_Werkorder_Voertuig FOREIGN KEY (VoertuigID) REFERENCES Werkplaats_Voertuigen(VoertuigID)
);

-- Table: Artikelen (Module: Magazijn)
CREATE TABLE Magazijn_Artikelen (
    ArtikelID INT PRIMARY KEY IDENTITY(1,1),
    ArtikelCode NVARCHAR(50) NOT NULL UNIQUE,
    Omschrijving NVARCHAR(200),
    Verkoopprijs DECIMAL(10, 2),
    VoorraadAantal INT DEFAULT 0,
    Locatie NVARCHAR(50)
);

-- Table: Facturen (Module: Financieel)
CREATE TABLE Financieel_Facturen (
    FactuurID INT PRIMARY KEY IDENTITY(20245000,1),
    WerkorderID INT,
    KlantID INT,
    TotaalBedrag DECIMAL(10, 2),
    BetaalStatus NVARCHAR(50) DEFAULT 'Openstaand', -- Openstaand, Betaald
    BetaalLink NVARCHAR(200),
    FactuurDatum DATETIME DEFAULT GETDATE(),
    CONSTRAINT FK_Factuur_Werkorder FOREIGN KEY (WerkorderID) REFERENCES Werkplaats_Werkorders(WerkorderID),
    CONSTRAINT FK_Factuur_Klant FOREIGN KEY (KlantID) REFERENCES Communicatie_Relaties(KlantID)
);

-- Seed Data

-- Klanten
INSERT INTO Communicatie_Relaties (KlantNaam, Telefoon, Email, Adres, Woonplaats)
VALUES 
('Jan de Vries', '0612345678', 'jan.devries@email.com', 'Dorpsstraat 1', 'Amsterdam'),
('Petra Jansen', '0687654321', 'petra.jansen@email.com', 'Kerkweg 22', 'Utrecht');

-- Voertuigen
INSERT INTO Werkplaats_Voertuigen (Kenteken, MerkNee, Model, KlantID, Bouwjaar)
VALUES 
('XX-99-XX', 'Volkswagen', 'Golf 8', 1, 2020),
('AB-123-C', 'Ford', 'Focus', 1, 2018),
('ZZ-00-ZZ', 'Tesla', 'Model 3', 2, 2022);

-- Werkorders
INSERT INTO Werkplaats_Werkorders (VoertuigID, Status, Omschrijving)
VALUES 
(1, 'Wacht op onderdelen', 'Grote beurt + Remblokken vervangen'),
(2, 'Klaar', 'APK Keuring'),
(3, 'Gepland', 'Winterbanden wissel');

-- Artikelen
INSERT INTO Magazijn_Artikelen (ArtikelCode, Omschrijving, Verkoopprijs, VoorraadAantal, Locatie)
VALUES 
('B-402', 'Remblokkenset Voor', 85.00, 10, 'A-01-02'),
('F-101', 'Oliefilter', 15.50, 0, 'B-02-05'), -- Out of stock
('APK-001', 'APK Keuring', 35.00, 999, 'DIENST');

-- Facturen
INSERT INTO Financieel_Facturen (WerkorderID, KlantID, TotaalBedrag, BetaalStatus, BetaalLink)
VALUES 
(2, 1, 35.00, 'Openstaand', 'https://pay.wincar.nl/ideal/top-garage/20245000');
