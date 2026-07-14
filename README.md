# **All-jellyfin-media-server**

<div style="text-align: center">
    <img src="image/Isyrr.png" style="margin: 15px 10px;">
</div>


Welcome to the All-jellyfin-media-server Repository! This repository contains everything you need to create your own media server with Jellyfin, Sonarr, Radarr, Seerr, Prowlarr, Jackett, qBittorrent, and FlareSolverr in a Docker Compose setup.

![](https://img.shields.io/github/stars/Morzomb/All-jellyfin-media-server.svg)
![](https://img.shields.io/github/forks/Morzomb/All-jellyfin-media-server.svg)
![](https://img.shields.io/github/release/Morzomb/All-jellyfin-media-server.svg) 
![](https://img.shields.io/github/issues/Morzomb/All-jellyfin-media-server.svg)
[![GitHub last commit](https://img.shields.io/github/last-commit/Morzomb/All-jellyfin-media-server.svg)](https://github.com/Morzomb/All-jellyfin-media-server/commits/master)
![GitHub repo size](https://img.shields.io/github/repo-size/Morzomb/All-jellyfin-media-server)
![visitors](https://visitor-badge.laobi.icu/badge?page_id=Morzomb.All-jellyfin-media-server.id)

## **Table of contents**

- [**All-jellyfin-media-server**](#all-jellyfin-media-server)
  - [**Table of contents**](#table-of-contents)
  - [**What is Isyrr for?**](#what-is-isyrr-for)
    - [**Jellyfin**](#jellyfin)
    - [**Seerr**](#seerr)
    - [**Sonarr**](#sonarr)
    - [**Radarr**](#radarr)
    - [**Jackett**](#jackett)
    - [**Flaresolverr**](#flaresolverr)
    - [**Prowlarr**](#prowlarr)
    - [**qBittorrent**](#qbittorrent)
- [**Prerequisites**](#prerequisites)
  - [**Docker**](#docker)
    - [**Using Docker Compose :**](#using-docker-compose-)
- [**Installation**](#installation)
- [**Accessing Applications**](#accessing-applications)
- [**Configuration Guide for Web Interfaces Only**](#configuration-guide-for-web-interfaces-only)
  - [**qBittorrent**](#qbittorrent-1)
    - [**Category Configuration**](#category-configuration)
  - [**Radarr**](#radarr-1)
    - [**Media Management**](#media-management)
    - [**Download Clients**](#download-clients)
    - [**Indexer Jackett (Optional)**](#indexer-jackett-optional)
  - [**Sonarr**](#sonarr-1)
    - [**Media Management**](#media-management-1)
    - [**Download Clients**](#download-clients-1)
    - [**Indexer Jackett (Optional)**](#indexer-jackett-optional-1)
  - [**Prowlarr**](#prowlarr-1)
    - [**Configure Torrent Indexers**](#configure-torrent-indexers)
    - [**Configure FlareSolverr**](#configure-flaresolverr)
    - [**Configure Radarr**](#configure-radarr)
    - [**Configure Sonarr**](#configure-sonarr)
  - [**Jellyfin**](#jellyfin-1)
    - [**Initial Setup**](#initial-setup)
    - [**Adding Users to Jellyfin**](#adding-users-to-jellyfin)
  - [**Seerr**](#seerr-configuration)
    - [**Sign In / Configuration**](#sign-in--configuration)
    - [**Integrating with Radarr**](#integrating-with-radarr)
    - [**Integrating with Sonarr**](#integrating-with-sonarr)
- [**Updating Applications**](#updating-applications)
- [**Disclaimer**](#disclaimer)

## **What is Isyrr for?**

This repository allows you to create your own Jellyfin media server with all the necessary tools to manage your movies, TV shows, music, and eBooks. It also includes tools to automate the downloading of new content.

This setup uses Docker and Docker Compose to deploy the services.

> [!IMPORTANT]  
> To use Docker Compose, make sure Docker is installed on your system.

---

### **Jellyfin**

[Jellyfin](https://jellyfin.org/) is an open-source media server software that allows you to stream your movies, TV shows, music, and eBooks to all your devices. It is compatible with many types of media files and supports streaming to numerous devices.

<div style="text-align: center">
    <img src="https://jellyfin.org/images/logo.svg" width="300" height="100"  style="margin: 15px 10px;">
</div>

### **Seerr**

[Seerr](https://docs.2seerr.dev/) is the unified successor to Jellyseerr and Overseerr. It automates media requests for Jellyfin, with Sonarr and Radarr integration for downloads.

### **Sonarr**

[Sonarr](https://sonarr.tv/) is TV show management software that allows you to search, download, and manage your favorite TV shows automatically. It works with many types of trackers and torrent clients and supports automatic subtitle downloading.


<div style="text-align: center">
    <img src="image/sonarr/sonarr.png" width="300" height="100" style="margin: 15px 10px;">
</div>

### **Radarr**

[Radarr](https://radarr.video/) is movie management software that allows you to search, download, and manage your favorite movies automatically. It works with many types of trackers and torrent clients and supports automatic subtitle downloading.

<div style="text-align: center">
    <img src="https://warlord0blog.files.wordpress.com/2022/01/radarr_logo-1.png" width="300" height="100" style="margin: 15px 10px;">
</div>

### **Jackett**

[Jackett](https://github.com/Jackett/Jackett) is a proxy software for torrent trackers that allows you to search for torrent files on many trackers from one place. It works with many types of torrent clients and supports authentication and advanced searching.

<div style="text-align: center">
    <img src="https://avatars.githubusercontent.com/u/15383019?s=280&v=4" width="100" height="100" style="margin: 15px 10px;">
</div>

### **Flaresolverr**

[Flaresolverr](https://github.com/FlareSolverr/FlareSolverr) is open-source software that allows you to bypass streaming restrictions on video-sharing sites. It works by resolving streaming links and bypassing geographical blocks and playback restrictions.

<div style="text-align: center">
    <img src="https://avatars.githubusercontent.com/u/75936191?v=4" width="200" height="200" style="margin: 15px 10px;">
</div>

### **Prowlarr**

[Prowlarr](https://github.com/Prowlarr/Prowlarr) is download management software that allows you to search for and automatically download files from many types of sources, including torrent trackers, newsgroups, and direct download sites.

<div style="text-align: center">
    <img src="https://prowlarr.com/logo/128.png" width="100" height="100" style="margin: 15px 10px;">
</div>

### **qBittorrent**

[qBittorrent](https://www.qbittorrent.org/) is open-source BitTorrent client software that allows you to download torrent files. It is lightweight, easy to use, and supports many advanced features such as built-in torrent search, encryption, torrent creation, and support for private trackers.

<div style="text-align: center">
    <img src="https://a.fsdn.com/allura/p/qbittorrent/icon?1518743661?&w=90" width="100" height="100" style="margin: 15px 10px;">
</div>

---

# **Prerequisites**

> [!NOTE]  
> This service requires a machine with at least 4 CPU cores and 8 GB of RAM.

Première chose à faire mettre à jour votre systèmes :

```bash
sudo apt update && sudo apt upgrade
```

## **Docker**

To install Docker on your system, use the following commands:

Download the script with this command:
```bash
curl -fsSL https://get.docker.com -o get-docker.sh
```

Then run the script with this command:
```bash
sh get-docker.sh
```

> [!TIP]
> I recommend giving Docker administrative rights to your user:
> ```bash
> usermod -aG docker <user>
> ```
> After this command, disconnect and reconnect.


### **Using Docker Compose :**

To use Docker Compose with this repository, navigate to the `compose_files/` directory and run the following command:

```bash
docker compose up -d
```
To shut down the stack :

```bash
docker compose down
```

**[`^        back to top        ^`](#table-of-contents)**

# **Installation**

First, clone the repository:

```bash
git clone https://github.com/Morzomb/All-jellyfin-media-server.git
cd All-jellyfin-media-server/
```

Before proceeding, copy `.env.example` into `.env` in the `compose_files/` directory, then update the values for your machine:

```bash
cp compose_files/.env.example compose_files/.env
```

```yaml
# BASE
COMMON_PATH=/YOUR_PATH/Isyrr
TZ=Europe/Paris
PUID=1000
PGID=1000
# Optional
JELLYFIN_PUBLISHED_SERVER_URL=
```

Validate the stack configuration before starting containers:

```bash
bash compose_files/validate.sh
```

To start the installation, execute:

```bash
cd compose_files/
docker compose -f docker-compose.yaml up -d
```

[Go to the file here](compose_files/docker-compose.yaml)

> [!NOTE]
> Jellyfin transcodes on CPU by default. Optional Intel/AMD VAAPI is available via `/dev/dri` if present on the host.

**[`^        back to top        ^`](#table-of-contents)**

# **Accessing Applications**

Once the applications are deployed, you can access them using the following addresses :

> [!IMPORTANT]  
> Replace `localhost` with the IP address of your machine or remote server if needed.


* Jellyfin : http://localhost:8096
* Seerr : http://localhost:5055
* Sonarr : http://localhost:8989
* Radarr : http://localhost:7878
* Jackett : http://localhost:9117
* Prowlarr : http://localhost:9696
* qBittorrent : http://localhost:8080
* FlareSolverr : http://localhost:8191

# **Configuration Guide for Web Interfaces Only**

> [!IMPORTANT]  
> All links containing the container name can be replaced with either the server IP or `localhost`. Also, replace `/COMMON_PATH/` with the path you configured in the `.env` file.


## **qBittorrent**

1. Open the WebUI by clicking on the application icon in the **DOCKER** tab and selecting **WebUI**.
2. Log in with the default credentials:
   - **Username**: `admin`
   - **Password**: `adminadmin`
   
<div style="text-align: center">
    <img src="image/qBittorrent/qbit1.png" style="margin: 15px 10px;">
</div>

   *Note: The default credentials may have changed, please check the documentation for updates on this. In most cases, qBittorrent Web UI will generate a temporary password when the container is started. To view this password, check container logs with: `docker compose logs qbittorrent`*

> [!WARNING]
> Change the qBittorrent default credentials immediately after first login.

1. Once logged in, click the gear icon to go to **Options**.
2. Under the **Downloads** tab, configure the backup settings as follows:
   - **Default Torrent Management Mode**: `Automatic` (required for category-based save paths to work)
   - **When Torrent Category changed**: `Relocate torrent`
   - **When Default Save Path changed**: `Relocate affected torrents`
   - **When Category Save Path changed**: `Relocate affected torrents`
   - **Default Save Path**: `/downloads` 
3. Click **SAVE**.

<div style="text-align: center">
    <img src="image/qBittorrent/qbit2.png" style="margin: 15px 10px;">
</div>

### **Category Configuration**

1. In the WebUI, expand **CATEGORIES** in the left menu. Right-click on **All** and select **Add category...**.
2. In the **New Category** window, configure as follows:
   - **Category**: `radarr` (this corresponds to the category you will later configure in Radarr)
   - **Save path**: `/downloads/radarr`
3. Click **Add**.
4. Right-click on **All** again, select **Add category...**.
5. Configure as follows:
   - **Category**: `sonarr` (this should match the category configured later in Sonarr, by default `sonarr-tv`, but this guide uses `sonarr`)
   - **Save path**: `/downloads/sonarr`
6. Click **Add**.

<div style="text-align: center">
    <img src="image/qBittorrent/qbit3.png" style="margin: 15px 10px;">
</div>

<div style="text-align: center">
    <img src="image/qBittorrent/qbit4.png" style="margin: 15px 10px;">
    <img src="image/qBittorrent/qbit5.png" style="margin: 15px 10px;">
</div>

**[`^        back to top        ^`](#table-of-contents)**

---

## **Radarr**

### **Media Management**

1. Open the WebUI and go to **Settings** > **Media Management**.
2. Click **Add Root Folder**, add the path `/COMMON_PATH/radarr/movies`, and click **OK**.
3. Click **Show Advanced** at the top, scroll down to **Importing**, and make sure **Use Hardlinks instead of Copy** is enabled.

<div style="text-align: center">
    <img src="image/radarr/rad3.png" style="margin: 15px 10px;">
</div>

### **Download Clients**

1. In the WebUI, go to **Settings** > **Download Clients**.
2. Click **+** under **Download Clients**, then select **qBittorrent** from the **Add Download Client** window.
3. Fill in the fields as follows:
   - **Name**: `qBittorrent` (or another name of your choice)
   - **Host**: `qbittorrent`
   - **Username**: `admin`
   - **Password**: `adminadmin` (change it if you've modified it in qBittorrent)
   - **Category**: `radarr` (this should match the category set in qBittorrent)
4. Click **Test**. If you see a checkmark, it means the connection is working; if not, there is an error.
5. Click **Save**.

<div style="text-align: center">
    <img src="image/radarr/rad5.png" style="margin: 15px 10px;">
</div>

_Note: if entering `qbittorrent` as the Host does not work, try entering the IP address instead (ex: `192.168.x.x`)_

> [!WARNING]
> On new installations, Radarr may complain that the `/downloads/radarr` directory does not exist inside the container (this is generally flagged as an error by Radarr in  **System** > **Status**). To fix this, simply move into the directory `/COMMON_PATH/qbittorrent/downloads` and manually create the `radarr` directory. Then, simply delete qBittorrent from Radarr and re-add it -  you should see the error disappear.

### **Indexer Jackett (Optional)**

1. In the WebUI, go to **Settings** > **Indexers**.
2. Click **+** under **Add Indexer**, then select **Torznab**.
3. Fill in the fields as follows:
   - **Name**: `Torznab` (or another name of your choice)
   - **URL**: `http://Jackett:9117/api/v2.0/indexers/YOUR_INDEXERS/results/torznab/`
   - **ApiKey**: Find the API key in the home menu at the top right.
4. Click **Test**. If you see a checkmark, it means the connection is working; if not, there is an error.
5. Click **Save**.

<div style="text-align: center">
    <img src="image/sonarr/son3.png" style="margin: 15px 10px;">
</div>

**[`^        back to top        ^`](#table-of-contents)**

---

## **Sonarr**

### **Media Management**

1. Open the WebUI and go to **Settings** > **Media Management**.
2. Click **Add Root Folder**, add the path `/COMMON_PATH/sonarr/tv`, and click **OK**.
3. Click **Show Advanced**, scroll down to **Importing**, and enable **Use Hardlinks instead of Copy**.

<div style="text-align: center">
    <img src="image/sonarr/son1.png" style="margin: 15px 10px;">
</div>

_Note: if entering `qbittorrent` as the Host does not work, try entering the IP address instead (ex: `192.168.x.x`)_

### **Download Clients**

1. In the WebUI, go to **Settings** > **Download Clients**.
2. Click **+** under **Download Clients**, then select **qBittorrent**.
3. Fill in the fields as follows:
   - **Name**: `qBittorrent` (or another name of your choice)
   - **Host**: `qbittorrent`
   - **Username**: `admin`
   - **Password**: `adminadmin` (change it if you've modified it in qBittorrent)
   - **Category**: `sonarr` (this should match the category set in qBittorrent)
4. Click **Test**. If you see a checkmark, it means the connection is working.
5. Click **Save**.

<div style="text-align: center">
    <img src="image/sonarr/son2.png" style="margin: 15px 10px;">
</div>

### **Indexer Jackett (Optional)**

1. In the WebUI, go to **Settings** > **Indexers**.
2. Click **+** under **Add Indexer**, then select **Torznab**.
3. Fill in the fields as follows:
   - **Name**: `Torznab` (or another name of your choice)
   - **URL**: `http://Jackett:9117/api/v2.0/indexers/YOUR_INDEXERS/results/torznab/`
   - **ApiKey**: Find the API key in the home menu at the top right.
4. Click **Test**. If you see a checkmark, it means the connection is working; if not, there is an error.
5. Click **Save**.

<div style="text-align: center">
    <img src="image/sonarr/son3.png" style="margin: 15px 10px;">
</div>

**[`^        back to top        ^`](#table-of-contents)**

---

## **Prowlarr**

### **Configure Torrent Indexers**

1. Open the WebUI and go to **Indexers** > **Add New Indexer**.
2. Select **1337x** (or another tracker of your choice).
   - You can modify the settings as per your preference, but the default values generally work well.
   - Sorting by **Seeders** can be useful for faster downloads.
3. Click **Test**. If you see a checkmark, the connection is functional; otherwise, there's an error.
4. Click **Save**.

### **Configure FlareSolverr**

1. Go to **Settings** and click **+** under **Indexer**.
2. Select **FlareSolverr** and fill in the information as follows:
   - **Name**: `FlareSolverr`
   - **Tags**: `flaresolverr`
   - **Host**: `http://flaresolverr:8191/`
3. Click **Test** to check the connection.
4. Click **Save**.

<div style="text-align: center">
    <img src="image/prowlarr/pro1.png" style="margin: 15px 10px;">
</div>

### **Configure Radarr**

1. Go to **Settings** and click **Apps**.
2. Select **Radarr** and fill in the information as follows:
   - **Sync Level**: `Full Sync`
   - **Prowlarr Server**: `http://prowlarr:9696`
   - **Radarr Server**: `http://radarr:7878`
   - **ApiKey**: Find the API key in the Radarr interface under **Settings** > **General** > **API Key**.
3. Click **Test** to check the connection.
4. Click **Save**.

<div style="text-align: center">
    <img src="image/prowlarr/pro2.png" style="margin: 15px 10px;">
</div>

### **Configure Sonarr**

1. Go to **Settings** and click **Apps**.
2. Select **Sonarr** and fill in the information as follows:
   - **Sync Level**: `Full Sync`
   - **Prowlarr Server**: `http://prowlarr:9696`
   - **Sonarr Server**: `http://sonarr:8989`
   - **ApiKey**: Find the API key in the Sonarr interface under **Settings** > **General** > **API Key**.
3. Click **Test** to check the connection.
4. Click **Save**.

<div style="text-align: center">
    <img src="image/prowlarr/pro3.png" style="margin: 15px 10px;">
</div>

**[`^        back to top        ^`](#table-of-contents)**

---

## **Jellyfin**

### **Initial Setup**

1. Open the Web UI by going to the **DOCKER** tab, click the app logo for Jellyfin, and select **WebUI**.
2. Select a preferred display language (or use the default English). Click **Next** ➝.
3. Create an administrator account, fill out the credentials as desired, and click **Next** ➝.
4. Click **Add Media Library** and fill in the following:
   - **Content type**: Movies
   - **Folders**: `/COMMON_PATH/radarr/movies`
   - Configure the rest as you see fit; the default settings are typically fine.
5. Click **OK**.
6. Click **Add Media Library** again and fill in the following:
   - **Content type**: Shows
   - **Folders**: `/COMMON_PATH/sonarr/tv`
   - Configure the rest as you see fit; the default settings are typically fine.
7. Click **OK**.
8. Click **Next** ➝.
9. Configure the **Preferred Metadata Language** (or use the default), and click **Next** ➝.
10. In **Configure Remote Access**, leave **Allow Remote Connections to this Server** checked and **Enable Automatic Port Mapping** unchecked.
11. Click **Next** ➝, then click **Finish**.
12. Sign in with your administrator account.

Once you sign in, if you already have media in your `/COMMON_PATH/*` folders, it should start appearing in Jellyfin. If not, the content will populate as the folders are filled.

### **Adding Users to Jellyfin**

If you want other users to access your Jellyfin server, you can create additional user accounts. This step is optional if you're the only user.

1. Open the left menu by clicking on the three horizontal lines (hamburger menu) in the upper left corner.
2. Select **Users** and click the **+** button on the left to add a new user.
3. Fill in the following details for the new user:
   - **Name**: `<username>`
   - **Password**: `<password>`
   - Under **Library Access**, check the boxes for the libraries (Movies, TV shows, etc.) that you want the user to have access to.
4. Click **Save** to create the user.
5. Repeat this process for all users you wish to add to the server.

**[`^        back to top        ^`](#table-of-contents)**

---

## **Seerr configuration**

> Config lives at `configs/jellyseerr` (unchanged path). Seerr migrates Jellyseerr data automatically on first start. See the [migration guide](https://docs.seerr.dev/migration-guide).

### **Sign In / Configuration**

1. Open the WebUI and select **Use your Jellyfin account** (existing setups skip the welcome flow after migration).
2. Fill in the information as follows:
   - **Jellyfin URL**: `http://jellyfin:8096/`
   - **Email Address**: `<your email address>`
   - **Username**: `<your Jellyfin username>`
   - **Password**: `<your Jellyfin password>`
3. Select **Sign In**.
4. Go to **Sync Libraries** under **Jellyfin Libraries**, select your Jellyfin libraries, then click **Continue**.

### **Integrating with Radarr**

1. Go to **Radarr Settings**, then click **Add Radarr Server**.
2. Fill in the information as follows:
   - **Default Server**: Check this box
   - **Server Name**: `Radarr`
   - **Name or IP Address**: `http://radarr`
   - **Port**: `7878`
   - **API Key**: Find the API key in the Radarr interface under **Settings** > **General** > **API Key**.
3. Click **Test** to check the connection.
4. Click **Save Changes**.

### **Integrating with Sonarr**

1. Go to **Sonarr Settings**, then click **Add Sonarr Server**.
2. Fill in the information as follows:
   - **Default Server**: Check this box
   - **Server Name**: `Sonarr`
   - **Name or IP Address**: `http://sonarr`
   - **Port**: `8989`
   - **API Key**: Find the API key in the Sonarr interface under **Settings** > **General** > **API Key**.
3. Click **Test** to check the connection.
4. Click **Save Changes**.

**[`^        back to top        ^`](#table-of-contents)**

---

# **Updating Applications**

The compose stack includes [Watchtower](https://github.com/nicholas-fedor/watchtower) (`watchtower` service), using the maintained [`nickfedor/watchtower`](https://hub.docker.com/r/nickfedor/watchtower) image so it works with current Docker Engine APIs (the original `containrrr/watchtower` image is unmaintained and errors on Docker 29+). It runs on a schedule, pulls newer images for labeled services, recreates those containers, and prunes old images (`WATCHTOWER_CLEANUP`). Only containers with the label `com.centurylinklabs.watchtower.enable=true` are updated (all services in `compose_files/docker-compose.yaml` inherit this from shared defaults), so other containers on the same Docker host are not touched. If you upgraded the compose file after containers were already created, recreate them once so the label is applied (for example `docker compose ... up -d --force-recreate`).

- Bring the updater online (from `compose_files` with your `.env` loaded): `docker compose -f docker-compose.yaml up -d watchtower`
- Optional: set `WATCHTOWER_POLL_INTERVAL` (seconds; default `21600` = every 6 hours while the host is on) or `WATCHTOWER_SCHEDULE` (6-field cron, quoted) in `compose_files/.env`. See `compose_files/.env.example`.
- One-off update of all labeled containers: `docker compose -f docker-compose.yaml run --rm watchtower --run-once`
- Logs: `docker logs -f watchtower`

**Manual updates** (if you prefer not to use Watchtower): stop the stack, remove old images, and recreate:

```bash
docker compose down
docker image prune -a
```

Then run `docker compose up -d` to restart the containers with the latest images.

**[`^        back to top        ^`](#table-of-contents)**

# **Disclaimer**

This code is provided for informational purposes only and should not be used for illegal activities. I am not responsible for the actions performed by users of this code. This code is for informational purposes, and if people wish to use it, they should consult the laws of their countries.
