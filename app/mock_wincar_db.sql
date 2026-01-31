-- ============================================
-- WinCar Mock Database v2.0
-- GarageAI Enhanced Schema
-- ============================================

-- Drop existing tables (in correct order for FK constraints)
IF OBJECT_ID('Financieel_Facturen', 'U') IS NOT NULL DROP TABLE Financieel_Facturen;
IF OBJECT_ID('Werkplaats_WerkorderRegels', 'U') IS NOT NULL DROP TABLE Werkplaats_WerkorderRegels;
IF OBJECT_ID('Werkplaats_Werkorders', 'U') IS NOT NULL DROP TABLE Werkplaats_Werkorders;
IF OBJECT_ID('Werkplaats_Voertuigen', 'U') IS NOT NULL DROP TABLE Werkplaats_Voertuigen;
IF OBJECT_ID('Communicatie_Relaties', 'U') IS NOT NULL DROP TABLE Communicatie_Relaties;
IF OBJECT_ID('Magazijn_Artikelen', 'U') IS NOT NULL DROP TABLE Magazijn_Artikelen;
IF OBJECT_ID('Magazijn_Categorieen', 'U') IS NOT NULL DROP TABLE Magazijn_Categorieen;
IF OBJECT_ID('Diensten_Services', 'U') IS NOT NULL DROP TABLE Diensten_Services;
IF OBJECT_ID('Diensten_Tarieven', 'U') IS NOT NULL DROP TABLE Diensten_Tarieven;

-- ============================================
-- COMMUNICATIE MODULE (CRM)
-- ============================================
CREATE TABLE Communicatie_Relaties (
    KlantID INT PRIMARY KEY IDENTITY(1,1),
    KlantNaam NVARCHAR(100) NOT NULL,
    Telefoon NVARCHAR(20),
    Email NVARCHAR(100),
    Adres NVARCHAR(200),
    Woonplaats NVARCHAR(100),
    AanmaakDatum DATETIME DEFAULT GETDATE()
);

-- ============================================
-- WERKPLAATS MODULE (Workshop)
-- ============================================
CREATE TABLE Werkplaats_Voertuigen (
    VoertuigID INT PRIMARY KEY IDENTITY(1,1),
    Kenteken NVARCHAR(20) NOT NULL UNIQUE,
    Merk NVARCHAR(50),
    Model NVARCHAR(50),
    KlantID INT,
    Bouwjaar INT,
    Brandstof NVARCHAR(20) DEFAULT 'Benzine',
    KilometerStand INT,
    LaatsteAPK DATE,
    CONSTRAINT FK_Voertuig_Klant FOREIGN KEY (KlantID) REFERENCES Communicatie_Relaties(KlantID)
);

CREATE TABLE Werkplaats_Werkorders (
    WerkorderID INT PRIMARY KEY IDENTITY(2024001,1),
    VoertuigID INT NOT NULL,
    KlantID INT,
    Status NVARCHAR(50) DEFAULT 'Gepland',
    Omschrijving NVARCHAR(MAX),
    AanmaakDatum DATETIME DEFAULT GETDATE(),
    GeplandeDatum DATETIME,
    AfmeldDatum DATETIME,
    Monteur NVARCHAR(50),
    CONSTRAINT FK_Werkorder_Voertuig FOREIGN KEY (VoertuigID) REFERENCES Werkplaats_Voertuigen(VoertuigID),
    CONSTRAINT FK_Werkorder_Klant FOREIGN KEY (KlantID) REFERENCES Communicatie_Relaties(KlantID)
);

CREATE TABLE Werkplaats_WerkorderRegels (
    RegelID INT PRIMARY KEY IDENTITY(1,1),
    WerkorderID INT NOT NULL,
    Type NVARCHAR(20) NOT NULL, -- 'ARBEID' or 'ONDERDEEL'
    Omschrijving NVARCHAR(200),
    Aantal DECIMAL(10,2) DEFAULT 1,
    PrijsPerEenheid DECIMAL(10,2),
    CONSTRAINT FK_Regel_Werkorder FOREIGN KEY (WerkorderID) REFERENCES Werkplaats_Werkorders(WerkorderID)
);

-- ============================================
-- MAGAZIJN MODULE (Warehouse/Parts)
-- ============================================
CREATE TABLE Magazijn_Categorieen (
    CategorieID INT PRIMARY KEY IDENTITY(1,1),
    Naam NVARCHAR(50) NOT NULL,
    Omschrijving NVARCHAR(200)
);

CREATE TABLE Magazijn_Artikelen (
    ArtikelID INT PRIMARY KEY IDENTITY(1,1),
    ArtikelCode NVARCHAR(50) NOT NULL UNIQUE,
    Omschrijving NVARCHAR(200),
    CategorieID INT,
    Inkoopprijs DECIMAL(10,2),
    Verkoopprijs DECIMAL(10,2),
    VoorraadAantal INT DEFAULT 0,
    MinimumVoorraad INT DEFAULT 2,
    Locatie NVARCHAR(50),
    CONSTRAINT FK_Artikel_Categorie FOREIGN KEY (CategorieID) REFERENCES Magazijn_Categorieen(CategorieID)
);

-- ============================================
-- DIENSTEN MODULE (Services & Pricing)
-- ============================================
CREATE TABLE Diensten_Services (
    ServiceID INT PRIMARY KEY IDENTITY(1,1),
    ServiceCode NVARCHAR(20) NOT NULL UNIQUE,
    Naam NVARCHAR(100) NOT NULL,
    Omschrijving NVARCHAR(500),
    StandaardPrijs DECIMAL(10,2),
    ArbeidUren DECIMAL(4,2),
    IsActief BIT DEFAULT 1
);

CREATE TABLE Diensten_Tarieven (
    TariefID INT PRIMARY KEY IDENTITY(1,1),
    Naam NVARCHAR(50) NOT NULL,
    UurTarief DECIMAL(10,2) NOT NULL,
    Omschrijving NVARCHAR(200)
);

-- ============================================
-- FINANCIEEL MODULE (Invoicing)
-- ============================================
CREATE TABLE Financieel_Facturen (
    FactuurID INT PRIMARY KEY IDENTITY(20240001,1),
    WerkorderID INT,
    KlantID INT,
    TotaalBedrag DECIMAL(10,2),
    BTWBedrag DECIMAL(10,2),
    BetaalStatus NVARCHAR(50) DEFAULT 'Openstaand',
    BetaalLink NVARCHAR(200),
    FactuurDatum DATETIME DEFAULT GETDATE(),
    BetaalDatum DATETIME,
    CONSTRAINT FK_Factuur_Werkorder FOREIGN KEY (WerkorderID) REFERENCES Werkplaats_Werkorders(WerkorderID),
    CONSTRAINT FK_Factuur_Klant FOREIGN KEY (KlantID) REFERENCES Communicatie_Relaties(KlantID)
);

-- ============================================
-- SEED DATA: CUSTOMERS (10)
-- ============================================
INSERT INTO Communicatie_Relaties (KlantNaam, Telefoon, Email, Adres, Woonplaats) VALUES
('Jan de Vries', '0612345678', 'jan.devries@email.nl', 'Dorpsstraat 1', 'Amsterdam'),
('Petra Jansen', '0687654321', 'petra.jansen@email.nl', 'Kerkweg 22', 'Utrecht'),
('Mohammed El Amrani', '0623456789', 'm.elamrani@email.nl', 'Hoofdstraat 45', 'Rotterdam'),
('Ingrid van der Berg', '0634567890', 'ingrid.vdberg@email.nl', 'Molenweg 8', 'Den Haag'),
('Pieter Bakker', '0645678901', 'p.bakker@email.nl', 'Stationsstraat 12', 'Eindhoven'),
('Fatima Yilmaz', '0656789012', 'f.yilmaz@email.nl', 'Parkstraat 33', 'Tilburg'),
('Willem Hendriks', '0667890123', 'w.hendriks@email.nl', 'Industrieweg 5', 'Groningen'),
('Sophie de Groot', '0678901234', 's.degroot@email.nl', 'Bosweg 17', 'Breda'),
('Thomas van Dijk', '0689012345', 't.vandijk@email.nl', 'Laan van Heuven 90', 'Nijmegen'),
('Lisa Vermeer', '0690123456', 'l.vermeer@email.nl', 'Bergstraat 41', 'Arnhem');

-- ============================================
-- SEED DATA: VEHICLES (15)
-- ============================================
INSERT INTO Werkplaats_Voertuigen (Kenteken, Merk, Model, KlantID, Bouwjaar, Brandstof, KilometerStand) VALUES
('XX-99-XX', 'Volkswagen', 'Golf 8', 1, 2020, 'Benzine', 45000),
('AB-123-C', 'Ford', 'Focus', 1, 2018, 'Diesel', 82000),
('ZZ-00-ZZ', 'Tesla', 'Model 3', 2, 2022, 'Elektrisch', 25000),
('HH-44-KK', 'Toyota', 'Yaris', 3, 2019, 'Hybride', 55000),
('PP-88-QQ', 'BMW', '320i', 4, 2021, 'Benzine', 35000),
('LL-22-MM', 'Audi', 'A4 Avant', 5, 2017, 'Diesel', 120000),
('RR-55-SS', 'Renault', 'Clio', 6, 2020, 'Benzine', 40000),
('DD-77-EE', 'Peugeot', '308', 7, 2019, 'Diesel', 75000),
('FF-33-GG', 'Mercedes', 'C-Klasse', 8, 2021, 'Benzine', 28000),
('JJ-66-NN', 'Opel', 'Corsa', 9, 2018, 'Benzine', 95000),
('BB-11-CC', 'Hyundai', 'i30', 10, 2020, 'Benzine', 38000),
('KK-99-LL', 'Kia', 'Sportage', 3, 2022, 'Hybride', 15000),
('MM-44-PP', 'Skoda', 'Octavia', 5, 2019, 'Diesel', 88000),
('VV-22-WW', 'Seat', 'Leon', 7, 2021, 'Benzine', 32000),
('YY-88-ZZ', 'Fiat', '500', 9, 2020, 'Benzine', 42000);

-- ============================================
-- SEED DATA: PART CATEGORIES
-- ============================================
INSERT INTO Magazijn_Categorieen (Naam, Omschrijving) VALUES
('Remmen', 'Remblokken, remschijven, remvloeistof'),
('Filters', 'Olie-, lucht-, brandstof-, interieurfilters'),
('Olie & Vloeistoffen', 'Motorolie, koelvloeistof, ruitenwisservloeistof'),
('Banden', 'Zomer-, winter-, all-season banden'),
('Verlichting', 'Lampen, koplampen, achterlichten'),
('Uitlaat', 'Uitlaatpijpen, katalysatoren, dempers'),
('Accu', 'Startaccu, hulpaccu'),
('Ruitenwissers', 'Wisserbladen voor en achter');

-- ============================================
-- SEED DATA: PARTS (50+)
-- ============================================
INSERT INTO Magazijn_Artikelen (ArtikelCode, Omschrijving, CategorieID, Inkoopprijs, Verkoopprijs, VoorraadAantal, Locatie) VALUES
-- Remmen (cat 1)
('REM-BLK-V', 'Remblokkenset Voor', 1, 45.00, 85.00, 12, 'A-01-01'),
('REM-BLK-A', 'Remblokkenset Achter', 1, 35.00, 65.00, 8, 'A-01-02'),
('REM-SCH-V', 'Remschijven Voor (set)', 1, 80.00, 145.00, 6, 'A-01-03'),
('REM-SCH-A', 'Remschijven Achter (set)', 1, 65.00, 115.00, 4, 'A-01-04'),
('REM-VLO', 'Remvloeistof DOT4 1L', 1, 8.00, 15.50, 20, 'A-01-05'),
-- Filters (cat 2)
('FIL-OLI-U', 'Oliefilter Universeel', 2, 5.00, 12.50, 25, 'B-02-01'),
('FIL-OLI-VW', 'Oliefilter VW/Audi', 2, 8.00, 18.50, 15, 'B-02-02'),
('FIL-OLI-BMW', 'Oliefilter BMW', 2, 12.00, 24.50, 10, 'B-02-03'),
('FIL-LCH-U', 'Luchtfilter Universeel', 2, 12.00, 28.00, 18, 'B-02-04'),
('FIL-LCH-VW', 'Luchtfilter VW Golf', 2, 15.00, 32.00, 8, 'B-02-05'),
('FIL-BRN', 'Brandstoffilter Diesel', 2, 18.00, 38.00, 12, 'B-02-06'),
('FIL-INT', 'Interieurfilter/Pollenfilter', 2, 10.00, 22.00, 20, 'B-02-07'),
-- Olie & Vloeistoffen (cat 3)
('OLI-5W30-5L', 'Motorolie 5W-30 5 Liter', 3, 25.00, 49.95, 30, 'C-03-01'),
('OLI-5W40-5L', 'Motorolie 5W-40 5 Liter', 3, 28.00, 54.95, 25, 'C-03-02'),
('OLI-0W20-5L', 'Motorolie 0W-20 5 Liter (Hybride)', 3, 35.00, 64.95, 15, 'C-03-03'),
('KOE-VLO-1L', 'Koelvloeistof G12+ 1 Liter', 3, 8.00, 16.95, 20, 'C-03-04'),
('KOE-VLO-5L', 'Koelvloeistof G12+ 5 Liter', 3, 30.00, 54.95, 10, 'C-03-05'),
('RUI-VLO-5L', 'Ruitenwisservloeistof 5L', 3, 3.00, 8.95, 40, 'C-03-06'),
-- Banden (cat 4)
('BND-ZOM-195', 'Zomerband 195/65R15', 4, 45.00, 79.00, 16, 'D-04-01'),
('BND-ZOM-205', 'Zomerband 205/55R16', 4, 55.00, 95.00, 12, 'D-04-02'),
('BND-WIN-195', 'Winterband 195/65R15', 4, 55.00, 95.00, 8, 'D-04-03'),
('BND-WIN-205', 'Winterband 205/55R16', 4, 65.00, 115.00, 8, 'D-04-04'),
('BND-4S-205', 'All-Season 205/55R16', 4, 70.00, 125.00, 4, 'D-04-05'),
-- Verlichting (cat 5)
('LMP-H7', 'Lamp H7 55W (2 stuks)', 5, 8.00, 18.95, 30, 'E-05-01'),
('LMP-H4', 'Lamp H4 60/55W (2 stuks)', 5, 10.00, 22.95, 25, 'E-05-02'),
('LMP-LED-H7', 'LED Lamp H7 Set', 5, 35.00, 69.95, 10, 'E-05-03'),
('LMP-KNP', 'Kentekenverlichting', 5, 3.00, 8.95, 20, 'E-05-04'),
-- Accu (cat 7)
('ACC-60AH', 'Startaccu 60Ah', 7, 65.00, 119.00, 6, 'G-07-01'),
('ACC-70AH', 'Startaccu 70Ah', 7, 75.00, 139.00, 4, 'G-07-02'),
('ACC-80AH', 'Startaccu 80Ah', 7, 90.00, 169.00, 3, 'G-07-03'),
-- Ruitenwissers (cat 8)
('WIS-V-600', 'Ruitenwisser Voor 600mm', 8, 8.00, 18.95, 15, 'H-08-01'),
('WIS-V-550', 'Ruitenwisser Voor 550mm', 8, 7.00, 16.95, 15, 'H-08-02'),
('WIS-A-400', 'Ruitenwisser Achter 400mm', 8, 6.00, 14.95, 12, 'H-08-03');

-- ============================================
-- SEED DATA: SERVICES & PRICING
-- ============================================
INSERT INTO Diensten_Services (ServiceCode, Naam, Omschrijving, StandaardPrijs, ArbeidUren) VALUES
('APK', 'APK Keuring', 'Algemene Periodieke Keuring voor personenauto', 35.00, 0.5),
('APK-HK', 'APK Herkeuring', 'Herkeuring na APK afkeur', 15.00, 0.25),
('BEURT-K', 'Kleine Beurt', 'Olie verversen, filters controleren, vloeistoffen bijvullen', 89.00, 1.0),
('BEURT-G', 'Grote Beurt', 'Volledige onderhoudsbeurt inclusief alle filters en vloeistoffen', 189.00, 2.0),
('BEURT-XL', 'Uitgebreide Beurt', 'Grote beurt + remmen + bougies/gloeibougies controle', 289.00, 3.0),
('REM-V', 'Remblokken Voor Vervangen', 'Remblokken voor vervangen inclusief controle remschijven', 149.00, 1.0),
('REM-A', 'Remblokken Achter Vervangen', 'Remblokken achter vervangen inclusief controle', 129.00, 1.0),
('REM-VLOE', 'Remvloeistof Verversen', 'Remvloeistof volledig verversen', 59.00, 0.5),
('BND-WIS', 'Banden Wisselen (4 stuks)', 'Seizoenswisseling banden op velg', 40.00, 0.5),
('BND-BAL', 'Banden Balanceren (4 stuks)', 'Wielen uitbalanceren', 35.00, 0.5),
('BND-MON', 'Banden Monteren (4 stuks)', 'Nieuwe banden monteren op velg', 60.00, 1.0),
('AIRCO', 'Airco Service', 'Airco bijvullen en lektest', 89.00, 1.0),
('AIRCO-DES', 'Airco Desinfectie', 'Airco reinigen en desinfecteren', 49.00, 0.5),
('DIAG', 'Diagnose Uitlezen', 'Storing uitlezen met diagnoseapparatuur', 45.00, 0.5),
('ACCU', 'Accu Vervangen', 'Nieuwe accu plaatsen inclusief registratie', 35.00, 0.5),
('LAMP-V', 'Lamp Vervangen Voor', 'Koplamp vervangen', 25.00, 0.25),
('LAMP-A', 'Lamp Vervangen Achter', 'Achterlicht vervangen', 20.00, 0.25),
('WISS', 'Ruitenwissers Vervangen', 'Wisserbladen vervangen voor en achter', 15.00, 0.25),
('INJ-REIN', 'Injectoren Reinigen', 'Brandstof injectoren reinigen', 79.00, 1.0),
('DIST-RIM', 'Distributieriem Vervangen', 'Distributieriem set vervangen', 450.00, 4.0);

-- ============================================
-- SEED DATA: LABOR RATES
-- ============================================
INSERT INTO Diensten_Tarieven (Naam, UurTarief, Omschrijving) VALUES
('Standaard', 75.00, 'Regulier uurtarief werkplaats'),
('Specialist', 95.00, 'Diagnose en specialistisch werk'),
('Express', 95.00, 'Spoedwerk / zelfde dag'),
('Elektrisch', 85.00, 'Elektrische voertuigen'),
('Klassiek', 85.00, 'Oldtimers en klassiekers');

-- ============================================
-- SEED DATA: WORK ORDERS (20)
-- ============================================
INSERT INTO Werkplaats_Werkorders (VoertuigID, KlantID, Status, Omschrijving, GeplandeDatum, Monteur) VALUES
(1, 1, 'In Behandeling', 'Grote beurt + remblokken voor vervangen', '2026-01-30 09:00', 'Erik'),
(2, 1, 'Klaar', 'APK Keuring - Goedgekeurd', '2026-01-28 14:00', 'Jan'),
(3, 2, 'Gepland', 'Winterbanden monteren', '2026-02-01 10:00', NULL),
(4, 3, 'Wacht op Onderdelen', 'Distributieriem vervangen - onderdeel besteld', '2026-02-03 08:00', 'Erik'),
(5, 4, 'In Behandeling', 'Kleine beurt', '2026-01-30 11:00', 'Marco'),
(6, 5, 'Gepland', 'APK + Grote beurt', '2026-02-05 09:00', NULL),
(7, 6, 'Klaar', 'Accu vervangen', '2026-01-29 15:00', 'Jan'),
(8, 7, 'Gefactureerd', 'Remblokken voor + achter', '2026-01-25 10:00', 'Erik'),
(9, 8, 'Gepland', 'Airco service', '2026-02-10 14:00', NULL),
(10, 9, 'In Behandeling', 'Diagnose motorstoring', '2026-01-30 13:00', 'Marco'),
(11, 10, 'Klaar', 'Ruitenwissers vervangen', '2026-01-29 16:00', 'Jan'),
(1, 1, 'Gepland', 'APK herkeuring', '2026-02-15 09:00', NULL),
(5, 4, 'Gefactureerd', 'Banden wisselen zomer→winter', '2026-11-15 10:00', 'Erik'),
(7, 6, 'Klaar', 'Lamp voor links vervangen', '2026-01-27 11:00', 'Marco'),
(12, 3, 'Gepland', 'Kleine beurt hybride', '2026-02-08 09:00', NULL);

-- ============================================
-- SEED DATA: INVOICES
-- ============================================
INSERT INTO Financieel_Facturen (WerkorderID, KlantID, TotaalBedrag, BTWBedrag, BetaalStatus) VALUES
(2024002, 1, 42.35, 7.35, 'Betaald'),
(2024007, 6, 144.00, 25.00, 'Betaald'),
(2024008, 7, 328.35, 57.00, 'Openstaand'),
(2024011, 10, 18.14, 3.14, 'Betaald'),
(2024013, 4, 48.40, 8.40, 'Betaald');