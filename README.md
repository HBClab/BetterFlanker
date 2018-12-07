# Flanker

## DataFiles

{% assign my_files = site.static_files | where:"extname",".svg" | sort:"modified_time" | reverse %}

{% capture sevendays %}{{'now' | date: "%s" | minus : 604800 }}{% endcapture %}

{% for img in my_files %}
    {% if img.name contains "swarmplot" %}
        {% capture file_mod %}{{img.modified_time | date: "%s"}}{% endcapture %}
        {% if file_mod > sevendays %}

### Recent

        {% else %}

### Older

        {% endif %}

#### **{{img.name}}**

![{{img.name}}]({{ img.path | prepend:site.baseurl }})
    {% endif %}
{% endfor %}

## Purpose

- Contains the code necessary to run task.

## Folders

- N/A

## Notes

- N/A

## Basic parameters

- N/A
